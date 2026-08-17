# webfile — an MCP server that attaches a file to a form in Chrome

One job, no project knowledge: **given an absolute path, a tab and a CSS selector, put that
file into that file input.** Nothing about CVs, `src/`, justjoin or pracuj lives here.

It exists because `claude-in-chrome`'s `file_upload` sends the extension a *path*, and an
extension cannot read the local disk — which is why the applier had to run in Cowork, whose
bridge reads the bytes host-side instead. This server takes the other route: the **Chrome
DevTools Protocol**, where `DOM.setFileInputFiles` makes the *browser process* read the file.
The sandbox never comes up.

## Prerequisite: a debuggable Chrome

CDP only exists if Chrome was **started** with the port open, and Chrome refuses that on the
default profile directory (otherwise any local program could silently drive the browser you
are logged into). So this uses a second profile:

```powershell
powershell -File tools\mcp_webfile\start_chrome.ps1     # port 9222, profile ~\chrome-mcp
```

One-time in that profile: log into the portals, install the Claude extension. It persists.
Your everyday Chrome is untouched and has no port open.

## Tools

| Tool | Purpose |
|---|---|
| `attach_file(file_path, url_contains, selector?, nth?)` | Attach the file; returns the filename the input actually holds afterwards |
| `find_file_inputs(url_contains, selector?)` | List every file input on a tab, iframes included, with the `nth` index for each |

### Why raw CDP and not Playwright — measured, `03`

The two routes differ in the one bit ARCHITECTURE.md §5B rates actions on:

| Route | `change` event `isTrusted` |
|---|---|
| `page.set_input_files()` | **false** — Playwright dispatches it from injected JS |
| `DOM.setFileInputFiles` | **true** — Chrome dispatches it at the input layer |

`isTrusted=false` is exactly why the `DataTransfer` workaround was rejected. So locating the
element (`DOM.performSearch`, the protocol's only cross-frame selector search) and the attach
itself go through CDP.

### Why no Playwright *at all*, not even to enumerate tabs — the 2026-08-16 outage, `04`

Playwright used to enumerate tabs here, and that alone broke the tool completely:

> `connect_over_cdp` attaches to **every** page in the browser and waits for all of them to
> initialise. Chrome suspends background tabs, and a suspended renderer answers no CDP
> command — so one sleeping tab, *any* tab, hung every call forever while the target tab was
> perfectly healthy. Measured: 101 commands sent, 30 never answered, all on two sleeping tabs.

A browser-wide connection is simply the wrong shape for a tool that touches one known tab.
Tabs now come from the plain HTTP `/json/list` endpoint — served by the browser process, so
it cannot hang — and the session is opened straight onto that one tab's target. Every command
carries a timeout, so a wedged renderer surfaces as a readable `ERROR:` instead of a hang.

The old symptom was maximally misleading: the server reported *"cannot reach Chrome … run
start_chrome.ps1"* while Chrome was up, the port open and the tab listed. That message now
fires only when the HTTP endpoint is genuinely unreachable.

**Waking a sleeping target tab** is `Page.bringToFront`, despite `Page.setWebLifecycleState`
being the one that sounds right — measured, the lifecycle command acks with `{}` and the
renderer stays dead. `bringToFront` activates the tab without reloading it, so anything
already typed into the form survives. It is applied to the target tab only.

Two more things it handles that a naive `page.set_input_files` does not:

- **Hidden inputs.** Upload buttons are normally a styled `<label>` over a hidden
  `<input type=file>`. Clicking opens an OS dialog no automation can drive; setting the
  input works and, this way, fires a genuine `change`, so React forms notice.
- **Iframes.** Embedded ATS forms live in one, and a page-level call only searches the main
  frame. `DOM.performSearch` crosses frames — a per-frame CDP session is not an option,
  since same-process iframes share the parent's session.

Failures come back as `ERROR: …` **return values**, not exceptions, so the model can read
what went wrong and retry. Ambiguity is a failure too: if `url_contains` matches more than
one tab it refuses and lists them, rather than guessing which tab gets the CV.

Setting a file the input **already holds** fires no `change` — it isn't a change. Harmless
here (the portal's pre-attached CV always has a different name), but it will confuse you if
you re-run a test twice.

The widget must already be on screen — open the upload dialog with the browser tools first,
then call `attach_file`.

## Build stages — each runnable on its own

```powershell
.venv\Scripts\python.exe tools\mcp_webfile\00_cdp_check.py         # Chrome reachable? tabs? inputs?
.venv\Scripts\python.exe tools\mcp_webfile\01_attach_test.py       # attach to all 3 input shapes
.venv\Scripts\python.exe tools\mcp_webfile\02_server_test.py       # real MCP handshake + tools/call
.venv\Scripts\python.exe tools\mcp_webfile\03_istrusted_test.py    # shipped tool vs the rejected hack
.venv\Scripts\python.exe tools\mcp_webfile\04_frozen_tab_test.py   # an unresponsive tab must not block
```

`03` and `04` exit non-zero on failure, so they work as regression checks: `03` guards the
§5B `isTrusted` bit, `04` guards against ever going back to a browser-wide connection. `04`
stages the outage on purpose — it opens its own throwaway tab, wedges that renderer with a
`while(true)`, attaches, and closes it. Chrome will not freeze a tab on demand (measured: it
ignores `setWebLifecycleState{frozen}` on a visible tab), so a wedged renderer is the only
deterministic way to reproduce it. Your own tabs are never touched.

`test_form.html` holds the three shapes (plain, hidden-behind-label, in-iframe). Its green
text is written by the page's own `change` handler, so it is proof the page really saw the
file — `01` asserts on that text, because setting `.files` without firing `change` is the
classic silent failure.

On Windows, `02` prints a `RuntimeError: Event loop is closed` during interpreter shutdown.
That is asyncio's subprocess teardown in the *test client*, after all assertions have passed;
Claude Code's own client is unaffected.

## Registration

```powershell
claude mcp add webfile -- "<repo>\.venv\Scripts\python.exe" "<repo>\tools\mcp_webfile\server.py"
```

Stored in `~/.claude.json` under this project. Tools appear as `mcp__webfile__attach_file`.

## Notes for editing

- **Never print to stdout** — that stream carries JSON-RPC and one stray line kills the
  connection. `log()` writes to stderr.
- The process is long-lived (one per session), but the CDP session is **per call** and closed
  in a `finally`. Do not reintroduce a cached connection: a localhost websocket costs
  milliseconds, and the cached one could not notice Chrome restarting or the tab closing.
- **Editing this? The server imports `attach.py` once, at startup.** Changes are invisible to
  a running Claude Code session until its `webfile` server is restarted (`/mcp` reconnect, or
  a new session). The numbered scripts always run the file on disk, so test with those first.
- `attach.py` is async because the stdio server runs an asyncio loop.
- The docstrings and type hints on the `@mcp.tool()` functions **are** the schema the model
  reads. Edit them as messages to the model.
- Requires `mcp` and `websockets` (both in `.venv`). Playwright is no longer used — see the
  outage note above before adding it back.
