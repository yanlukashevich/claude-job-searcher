r"""Stage 0: prove the debuggable Chrome is reachable and see what is on it. No MCP involved.

Run:  .venv\Scripts\python.exe tools\mcp_webfile\00_cdp_check.py

Chrome must already be running from start_chrome.ps1 (or any Chrome started with
--remote-debugging-port=9222 and a non-default --user-data-dir).

Reports each tab's renderer state, because a frozen tab is the failure mode that used to
look like "Chrome is not running": Memory Saver suspends background tabs and a frozen
renderer answers no CDP command. attach.py wakes its target tab; this shows you which tabs
were asleep.
"""

import asyncio
import sys

from attach import CDP_URL, CdpError, _find, _http_json, page_session


async def scan(target):
    """Responsiveness + file inputs for one tab, without ever touching another."""
    async with page_session(target["url"]) as (cdp, _):
        return await _find(cdp, "input[type=file]")


async def main():
    try:
        version = await _http_json("/json/version")
        targets = await _http_json("/json/list")
    except CdpError as err:
        sys.exit(f"{err}\n\nStart Chrome first: start_chrome.ps1")

    pages = [t for t in targets if t.get("type") == "page"]
    print(f"connected  {CDP_URL}")
    print(f"browser    {version.get('Browser')}")
    print(f"targets    {len(targets)} total, {len(pages)} pages\n")

    print("open tabs (and their file inputs):")
    found = 0
    for t in pages:
        print(f"  {t['url'][:88]}")
        try:
            hits = await scan(t)
        except CdpError as err:
            print(f"      !! {err}")
            continue
        for node_id, p in hits:
            found += 1
            ident = p["id"] or p["name"] or "(no id/name)"
            print(f"      {p['frame']:6}  #{ident:22}  "
                  f"{'visible' if p['shown'] else 'hidden ':7}  "
                  f"holds: {p['file'] or '(empty)'}")

    if not found:
        print("\n  no file inputs anywhere -- open tools\\mcp_webfile\\test_form.html in that Chrome")


if __name__ == "__main__":
    asyncio.run(main())
