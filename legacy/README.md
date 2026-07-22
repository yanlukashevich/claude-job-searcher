# legacy/ — the superseded PowerShell collection pipeline

These three files were the original offer-collection + worklist layer. They are **frozen for
reference**, not maintained. The `finder/` Python cockpit replaced all of them.

| file | did what | replaced by |
|---|---|---|
| `harvest_offers.ps1` | pulled the justjoin.it API into `offers_queue.json` | `finder/harvest.py` → `finder/data/offers_db.jsonl` |
| `offers_queue.json` | the harvested queue (Finder output, applier input) | `finder/data/offers_db.jsonl` |
| `build_worklist.ps1` | `status:pending` + dedup vs the log + `-Limit` → `src/worklist.json` | the finder cockpit's **Write worklist** button (`finder/app.py`) |

**They no longer run in place.** `build_worklist.ps1` resolves paths from its own location, so
from `legacy/` it would look for `legacy/src/` and `legacy/offers_queue.json`. Do not run them;
use the finder (`finder/README.md`). Kept only so the old schema and the dedup logic stay
readable if the finder ever needs to be checked against them.
