r"""Stage 3: is the shipped attach_file's `change` event REAL, or synthetic?

Run:  .venv\Scripts\python.exe tools\mcp_webfile\03_istrusted_test.py

ARCHITECTURE.md 5B rates every browser action on `event.isTrusted`, and the DataTransfer
workaround (input.files = dt.files; dispatchEvent(new Event('change'))) was rejected for
producing isTrusted=false -- a script-made event any anti-bot script can flag.

This asserts the shipped tool clears that bar, and shows the rejected hack failing it in
the same run, so the comparison is measured rather than remembered.
"""

import asyncio
import sys
from pathlib import Path

from attach import CdpError, attach_file, page_session

TAB = "test_form.html"
CV = Path(__file__).resolve().parents[2] / "src/CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich.pdf"

# The clear matters: setting a file an input already holds is not a change, and fires nothing.
WATCH = """(() => {
    window.__probe = null;
    const el = document.getElementById('plain');
    el.value = '';
    el.addEventListener('change', e => {
        window.__probe = {isTrusted: e.isTrusted, type: e.type, name: e.target.files[0]?.name};
    }, {once: true});
})()"""

FAKE = """(() => {
    window.__probe = null;
    const el = document.getElementById('plain');
    el.addEventListener('change', e => {
        window.__probe = {isTrusted: e.isTrusted, type: e.type, name: e.target.files[0]?.name};
    }, {once: true});
    const dt = new DataTransfer();
    dt.items.add(new File(['x'], 'fake.pdf', {type: 'application/pdf'}));
    el.files = dt.files;
    el.dispatchEvent(new Event('change', {bubbles: true}));
})()"""

PROBE = "window.__probe"


async def main():
    try:
        async with page_session(TAB) as (cdp, _):
            await cdp.evaluate(WATCH)

        print("attach_file (shipped):", await attach_file(CV, TAB, "#plain"))

        async with page_session(TAB) as (cdp, _):
            real = await cdp.evaluate(PROBE)
            print("            event:", real, "\n")

            await cdp.evaluate(FAKE)
            fake = await cdp.evaluate(PROBE)
    except CdpError as err:
        sys.exit(f"ERROR: {err}")

    print("DataTransfer hack (rejected by 5B):")
    print("            event:", fake, "\n")

    ok = real and real["isTrusted"] is True and fake and fake["isTrusted"] is False
    print("VERDICT:", "attach_file fires a genuine browser event -- 5B satisfied" if ok
          else f"FAIL -- shipped={real} hack={fake}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
