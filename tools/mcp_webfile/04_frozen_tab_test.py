r"""Stage 4: an unresponsive tab elsewhere in Chrome must not stop an attach. The 2026-08-16 bug.

Run:  .venv\Scripts\python.exe tools\mcp_webfile\04_frozen_tab_test.py

WHAT THIS REPLACES. Until 2026-08-16 this slot held a Playwright-vs-CDP comparison of the
`change` event's isTrusted bit. That question is settled, 03 still measures the bit that
matters (shipped tool vs the DataTransfer hack), and Playwright is no longer used by this
tool at all -- so a regression test for it guarded nothing. The live risk is the failure
that removed it:

    Chrome suspends background tabs, and a suspended renderer answers no CDP command.
    Playwright's connect_over_cdp attaches to EVERY page and waits for all of them, so one
    sleeping tab -- any tab, not the one being used -- hung every call for good, while the
    target tab was perfectly healthy.

attach.py now opens a session on exactly one target. This proves it by staging the condition
on purpose.

WHY A WEDGED RENDERER AND NOT A FROZEN ONE. Chrome will not freeze on demand: measured, it
ignores `Page.setWebLifecycleState{frozen}` on a visible tab, and which background tabs it
has put to sleep is its own business, so a test cannot rely on one existing. A `while(true)`
in a throwaway tab blocks that renderer's main thread the same way, deterministically, and
touches nothing the user has open. It cannot be undone -- the tab is closed at the end.
"""

import asyncio
import json
import sys
import urllib.request
from pathlib import Path

import websockets

from attach import CDP_URL, CdpError, _http_json, attach_file, pick_target

TAB = "test_form.html"
CV = Path(__file__).resolve().parents[2] / "src/CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich.pdf"


def _http(path, method):
    """/json/new and /json/close need verbs urllib will not send by default."""
    req = urllib.request.Request(CDP_URL + path, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


async def wedge(decoy):
    """Block the decoy's main thread forever. Returns True once it stops answering."""
    ws = await websockets.connect(decoy["webSocketDebuggerUrl"], max_size=None)
    # Never awaited: the evaluate cannot return, that is the point.
    await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                              "params": {"expression": "while(true){}"}}))
    await asyncio.sleep(1)
    await ws.send(json.dumps({"id": 2, "method": "Runtime.evaluate",
                              "params": {"expression": "1", "returnByValue": True}}))
    try:
        await asyncio.wait_for(ws.recv(), timeout=5)
        return False
    except asyncio.TimeoutError:
        return True
    finally:
        await ws.close()


async def main():
    pick_target(await _http_json("/json/list"), TAB)  # fail early if the form tab is not open

    decoy = _http("/json/new?about:blank", "PUT")
    print(f"decoy tab     {decoy['id']}")
    try:
        if not await wedge(decoy):
            sys.exit("could not wedge the decoy tab -- test inconclusive")
        print("wedged it     (renderer no longer answers CDP)\n")

        started = asyncio.get_event_loop().time()
        result = await attach_file(CV, TAB, "#plain")
        took = asyncio.get_event_loop().time() - started
    finally:
        _http(f"/json/close/{decoy['id']}", "GET")
        print("closed decoy")

    print(f"\nattach with an unresponsive tab open: {result}")
    print(f"took {took:.1f}s")

    ok = result.startswith("attached")
    print("\nVERDICT:", "an unresponsive tab elsewhere no longer blocks the attach" if ok
          else f"FAIL -- {result}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if not CV.is_file():
        sys.exit(f"test CV not found: {CV}")
    try:
        asyncio.run(main())
    except CdpError as err:
        sys.exit(f"ERROR: {err}")
