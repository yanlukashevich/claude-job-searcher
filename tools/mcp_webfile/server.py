r"""webfile -- an MCP server with one job: attach a local file to a file input in Chrome.

It knows nothing about any project. Give it a path, a tab and a selector.

Register once (from the project root):

    claude mcp add webfile -- "c:\Users\yanlu\prog\claude_job_seracher\.venv\Scripts\python.exe" ^
                              "c:\Users\yanlu\prog\claude_job_seracher\tools\mcp_webfile\server.py"

Chrome must be running with the DevTools port open -- see start_chrome.ps1. That port is
what lets this work at all: `DOM.setFileInputFiles` makes the BROWSER PROCESS read the file,
so the sandboxed extension's inability to read local paths never comes up.

Each call opens its own short-lived CDP session on the one tab it was asked about, and
closes it in a `finally`. There is deliberately no cached browser-wide connection: the
previous version kept one and it was the bug -- see attach.py's header. A localhost
websocket costs milliseconds, and per-call sessions cannot go stale when Chrome restarts or
the tab closes.

Nothing may be printed to stdout -- that stream carries JSON-RPC, and one stray line kills
the connection. Logs go to stderr.
"""

import sys

from mcp.server.mcpserver import MCPServer

from attach import attach_file as _attach, describe_inputs as _describe

mcp = MCPServer("webfile")


def log(msg):
    print(f"[webfile] {msg}", file=sys.stderr, flush=True)


@mcp.tool()
async def attach_file(file_path: str, url_contains: str,
                      selector: str = "input[type=file]", nth: int = 0) -> str:
    """Attach a local file to a file input on an already-open Chrome tab.

    Works on hidden inputs (the usual case: a styled button over a hidden field) and on
    inputs inside iframes. The upload widget must already be on screen -- open the dialog
    first, then call this.

    Args:
        file_path: Absolute path on the user's machine, e.g. C:\\Users\\me\\cv.pdf
        url_contains: Substring identifying the tab; must match exactly one open tab.
        selector: CSS selector for the input. Default finds any file input.
        nth: Which match to use when several exist. See find_file_inputs for the indices.

    Returns the filename the input actually holds afterwards, or a string starting with
    ERROR: explaining what to fix.
    """
    result = await _attach(file_path, url_contains, selector, nth)
    log(result)
    return result


@mcp.tool()
async def find_file_inputs(url_contains: str, selector: str = "input[type=file]") -> str:
    """List every file input on a tab, including ones inside iframes.

    Use this when attach_file reports it found nothing, or when a page has several upload
    fields and you need the right `nth`.

    Args:
        url_contains: Substring identifying the tab; must match exactly one open tab.
        selector: CSS selector to look for. Default finds any file input.
    """
    return await _describe(url_contains, selector)


if __name__ == "__main__":
    log("starting on stdio")
    mcp.run("stdio")
