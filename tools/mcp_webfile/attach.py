r"""The one job: put a local file into a file input on an already-open page.

Knows nothing about any project -- it takes a path, a tab, and a selector. Shared by the
numbered test scripts and server.py, so there is one implementation.

WHY RAW CDP AND NOT playwright's set_input_files (measured, 03 vs 04):

    set_input_files          change event isTrusted = FALSE   <- Playwright dispatches it
                                                                 from injected JS
    DOM.setFileInputFiles    change event isTrusted = TRUE    <- Chrome dispatches it at
                                                                 the input layer

ARCHITECTURE.md 5B rates browser actions on exactly that bit, and the DataTransfer
workaround was rejected for failing it. So every DOM read and the attach itself go through
the protocol.

WHY NO PLAYWRIGHT AT ALL, NOT EVEN TO ENUMERATE TABS (measured 2026-08-16):

    `connect_over_cdp` attaches to EVERY page in the browser and waits for all of them to
    initialise. Chrome's Memory Saver freezes background tabs, and a frozen renderer answers
    no CDP command -- so one sleeping tab anywhere in a real user's Chrome hung the connect
    forever, with the target tab perfectly healthy. Measured: 101 commands sent, 30 never
    answered, all of them on two frozen background tabs.

    A browser-wide connection is the wrong shape for a tool that touches ONE known tab. So
    tabs come from the plain HTTP `/json/list` endpoint (which cannot hang -- the browser
    process serves it) and the session is opened straight onto that one tab's target. Other
    tabs, frozen or not, are never touched.

Every command carries a timeout for the same reason: a wedged renderer must surface as a
readable ERROR, not as a hang with no output.

Async because the MCP stdio server already runs an asyncio loop.
"""

import asyncio
import json
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path

import websockets

CDP_URL = "http://127.0.0.1:9222"
CMD_TIMEOUT = 15  # seconds; a healthy renderer answers in milliseconds
WAKE_TIMEOUT = 10

# Runs on the resolved element, in its own frame's context.
_DESCRIBE = """function () {
    return {tag: this.tagName, type: this.type, id: this.id, name: this.name,
            accept: this.accept, multiple: !!this.multiple, shown: !!this.offsetParent,
            file: (this.files && this.files[0]) ? this.files[0].name : '',
            frame: this.ownerDocument.defaultView === window.top ? 'main' : 'iframe'};
}"""

_TEXT = """function () {
    return {tag: this.tagName, text: (this.innerText || '').trim()};
}"""


class CdpError(Exception):
    """Anything the caller should hand back as `ERROR: ...` for the model to read."""


# --------------------------------------------------------------------------- transport


async def _http_json(path):
    """The DevTools HTTP endpoint. Served by the browser process, so no renderer can wedge it."""

    def fetch():
        with urllib.request.urlopen(CDP_URL + path, timeout=5) as resp:
            return json.load(resp)

    try:
        return await asyncio.to_thread(fetch)
    except Exception as exc:
        raise CdpError(f"cannot reach Chrome at {CDP_URL} ({exc.__class__.__name__}). "
                       f"Chrome must be started by start_chrome.ps1 -- ask the user to "
                       f"run it.") from exc


class CDP:
    """A request/response CDP session on ONE page target. Events are discarded unread."""

    def __init__(self, ws):
        self._ws = ws
        self._next = 0

    async def send(self, method, params=None, timeout=CMD_TIMEOUT):
        self._next += 1
        msg_id = self._next
        await self._ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        try:
            reply = await asyncio.wait_for(self._reply(msg_id), timeout)
        except asyncio.TimeoutError:
            raise CdpError(f"{method} got no reply in {timeout}s -- that tab's renderer is "
                           f"not responding (frozen or wedged)") from None
        if "error" in reply:
            raise CdpError(f"{method} failed: {reply['error'].get('message', reply['error'])}")
        return reply.get("result", {})

    async def _reply(self, msg_id):
        while True:
            msg = json.loads(await self._ws.recv())
            if msg.get("id") == msg_id:
                return msg

    async def evaluate(self, expression):
        """Run JS in the tab's main frame and return it by value."""
        got = await self.send("Runtime.evaluate", {"expression": expression,
                                                   "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in got:
            raise CdpError(f"page threw: {got['exceptionDetails'].get('text')}")
        return got["result"].get("value")


def pick_target(targets, url_contains):
    """The one open tab whose URL contains `url_contains`.

    Ambiguity is an error, not a guess -- attaching to the wrong tab is worse than failing.
    """
    pages = [t for t in targets if t.get("type") == "page"]
    hits = [t for t in pages if url_contains in t.get("url", "")]
    if not hits:
        raise CdpError(f"no tab whose URL contains {url_contains!r}. "
                       f"Open tabs: {[t.get('url', '') for t in pages]}")
    if len(hits) > 1:
        raise CdpError(f"{len(hits)} tabs match {url_contains!r} -- narrow it. "
                       f"Matches: {[t['url'] for t in hits]}")
    return hits[0]


async def _wake(cdp):
    """Chrome suspends background tabs, and a suspended renderer answers no CDP command.

    Measured 2026-08-16, on tabs Chrome had actually put to sleep:

        Page.setWebLifecycleState{active}   acks with {} and the renderer stays dead
        Page.bringToFront                   acks and the renderer answers again

    So it is bringToFront, despite the lifecycle command being the one that sounds right.
    It activates the tab without reloading it, so anything already typed into the form
    survives. Only ever applied to the one target tab.

    Tolerated if it fails: on a healthy tab it is a cheap no-op, and if the tab is wedged for
    some other reason the next command reports that properly instead of this hiding it.
    """
    try:
        await cdp.send("Page.bringToFront", timeout=WAKE_TIMEOUT)
    except CdpError:
        pass


@asynccontextmanager
async def page_session(url_contains):
    """A CDP session on the single tab matching `url_contains`, woken and ready."""
    target = pick_target(await _http_json("/json/list"), url_contains)
    ws_url = target.get("webSocketDebuggerUrl")
    if not ws_url:
        raise CdpError(f"tab exposes no debugger endpoint (another client already attached?): "
                       f"{target.get('url', '')}")
    try:
        ws = await asyncio.wait_for(websockets.connect(ws_url, max_size=None), CMD_TIMEOUT)
    except Exception as exc:
        raise CdpError(f"cannot open a CDP session on {target.get('url', '')} "
                       f"({exc.__class__.__name__})") from exc
    try:
        cdp = CDP(ws)
        await _wake(cdp)
        yield cdp, target
    finally:
        await ws.close()


# --------------------------------------------------------------------------- DOM search


async def _props(cdp, node_id, fn):
    """Call `fn` on a node with `this` bound to it, or None if the node has gone away."""
    try:
        resolved = await cdp.send("DOM.resolveNode", {"nodeId": node_id})
        got = await cdp.send("Runtime.callFunctionOn", {
            "objectId": resolved["object"]["objectId"],
            "functionDeclaration": fn, "returnByValue": True})
        return got["result"]["value"]
    except CdpError:
        return None


async def _search(cdp, selector):
    """Every node matching `selector`, iframes included.

    DOM.performSearch is the only cross-frame selector search in the protocol; a per-frame
    session is not an option, since same-process iframes share the parent's session. It also
    matches plain text, so callers must filter the results down to what they wanted.
    """
    await cdp.send("DOM.enable", {})
    await cdp.send("DOM.getDocument", {"depth": -1, "pierce": True})
    search = await cdp.send("DOM.performSearch", {"query": selector})
    try:
        if not search["resultCount"]:
            return []
        got = await cdp.send("DOM.getSearchResults", {
            "searchId": search["searchId"], "fromIndex": 0, "toIndex": search["resultCount"]})
    finally:
        await cdp.send("DOM.discardSearchResults", {"searchId": search["searchId"]})
    return got["nodeIds"]


async def _find(cdp, selector):
    """(node_id, props) for every file input matching `selector`."""
    # performSearch also matches plain text, so `#hidden` can return the <style> rule that
    # mentions it. Undefined properties are dropped from returnByValue, hence .get().
    out = []
    for node_id in await _search(cdp, selector):
        props = await _props(cdp, node_id, _DESCRIBE)
        if props and props.get("tag") == "INPUT" and props.get("type") == "file":
            out.append((node_id, props))
    return out


async def text_of(cdp, selector):
    """innerText of the first element matching `selector` in any frame, '' if there is none.

    Used by the tests to read what the PAGE wrote -- proof its own change handler ran.
    """
    for node_id in await _search(cdp, selector):
        props = await _props(cdp, node_id, _TEXT)
        if props and props.get("tag"):
            return props.get("text", "")
    return ""


# --------------------------------------------------------------------------- public API


async def attach_file(file_path, url_contains, selector="input[type=file]", nth=0):
    """Returns a short string either way -- the model reads it and retries, so failures are
    return values, not exceptions."""
    path = Path(file_path)
    if not path.is_file():
        return f"ERROR: no such file: {path}"

    try:
        async with page_session(url_contains) as (cdp, target):
            hits = await _find(cdp, selector)
            if not hits:
                return (f"ERROR: no file input matching {selector!r} in any frame of "
                        f"{target['url']} -- is the upload dialog open yet? "
                        f"Try find_file_inputs.")
            if nth >= len(hits):
                return f"ERROR: nth={nth} but only {len(hits)} file inputs match {selector!r}"

            node_id, _ = hits[nth]
            await cdp.send("DOM.setFileInputFiles",
                           {"files": [str(path.resolve())], "nodeId": node_id})

            after = await _props(cdp, node_id, _DESCRIBE)
            landed = (after or {}).get("file", "")
            if not landed:
                return f"ERROR: set the file but the input reads back empty ({selector!r} #{nth})"
            return (f"attached {landed} to {selector!r} #{nth} of {len(hits)} "
                    f"({after['frame']} frame) on {target['url']}")
    except CdpError as err:
        return f"ERROR: {err}"


async def describe_inputs(url_contains, selector="input[type=file]"):
    """What upload fields does this tab actually have? Same ordering as attach_file's `nth`."""
    try:
        async with page_session(url_contains) as (cdp, target):
            hits = await _find(cdp, selector)
            if not hits:
                return f"no file input matching {selector!r} in any frame of {target['url']}"

            lines = []
            for i, (_, p) in enumerate(hits):
                ident = p["id"] or p["name"]
                lines.append(f"[{i}] {p['frame']:6} | {'#' + ident if ident else '(no id/name)'} | "
                             f"{'visible' if p['shown'] else 'hidden'} | "
                             f"accept={p['accept'] or '*'}"
                             f"{' | multiple' if p['multiple'] else ''}"
                             f"{' | holds ' + p['file'] if p['file'] else ''}")
            return (f"{len(hits)} file input(s) matching {selector!r} on {target['url']}\n"
                    + "\n".join(lines)
                    + "\n(the [n] index is the `nth` argument of attach_file)")
    except CdpError as err:
        return f"ERROR: {err}"
