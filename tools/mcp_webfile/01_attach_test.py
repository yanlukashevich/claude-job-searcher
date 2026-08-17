r"""Stage 1: attach a real file to all three input shapes. Still no MCP.

Run:  .venv\Scripts\python.exe tools\mcp_webfile\01_attach_test.py [path-to-file]

Chrome from start_chrome.ps1 must be open on test_form.html. Watch the window: the green
text next to each field is written by the page's own `change` handler, so if it appears,
a framework on a real site would have seen the file too. This script checks that text
itself -- setting `.files` without firing `change` is the classic silent failure.
"""

import asyncio
import sys
from pathlib import Path

from attach import attach_file, describe_inputs, page_session, text_of

TAB = "test_form.html"

DEFAULT_FILE = (Path(__file__).resolve().parents[2]
                / "src/CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich.pdf")

CASES = [
    ("1 plain visible input", "#plain", "#out-plain"),
    ("2 hidden behind label", "#hidden", "#out-hidden"),
    ("3 inside an iframe", "#framed", "#out"),
]


async def readout(selector):
    """Read the text the PAGE wrote -- proof the change event actually fired."""
    async with page_session(TAB) as (cdp, _):
        return await text_of(cdp, selector)


async def main(file_path):
    print(f"uploading  {file_path.name}  ({file_path.stat().st_size} bytes)\n")

    for label, selector, out_sel in CASES:
        print(f"{label:24} {await attach_file(file_path, TAB, selector)}")
        shown = await readout(out_sel)
        verdict = "change event fired" if shown else "NO change event -- page never noticed"
        print(f"{'':24} page shows: {shown or '(nothing)':40} <- {verdict}\n")

    print("describe_inputs:")
    print(await describe_inputs(TAB), "\n")

    # Error paths matter as much as the happy one: the model reads these strings.
    print("error handling:")
    print("  bad path  :", await attach_file("C:/nope.pdf", TAB))
    print("  bad tab   :", (await attach_file(file_path, "no-such-tab-xyz"))[:100])
    print("  bad select:", (await attach_file(file_path, TAB, "#nope"))[:100])


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE
    if not path.is_file():
        sys.exit(f"no such file: {path}\nPass one as an argument.")
    asyncio.run(main(path))
