"""The cockpit's "Write worklist" button, without the human. Run hourly by Task Scheduler.

Picks 5 offers and writes src/worklist.json exactly as clicking the button would. The rules
it stands in for -- the ones you apply by eye when you tick boxes:

  live          not expired (every portal carrying it has dropped it -> skip)
  unapplied     neither the bot log nor your manual marks name any of the offer's links
  lone posting  the company has exactly ONE live offer in the db (a small employer; a
                corporation posting fifteen roles is a different kind of application)
  not killed    the KILL bucket is off-stack by keyword, never worth a slot
  best first    highest score, your manual_scores.json overrides included

It imports app.py rather than re-deriving any of that. Applied-status joins on ALL of an
offer's URLs, one employer spells its name six ways, a manual score override replaces the
sort key -- every one of those is already solved there, and a second implementation would
drift from the cockpit silently, which is the one failure you would not see.

Importing app.py builds the FastAPI object but starts no server (uvicorn runs under its
__main__), so this stays a plain offline script: it reads the db harvest.py already wrote and
never touches the network.

  python finder/auto_worklist.py --dry-run     # show the picks, write nothing
  python finder/auto_worklist.py               # write src/worklist.json
"""
import argparse
import collections
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from app import WORKLIST, WorklistBody, api_offers, api_worklist   # noqa: E402
from common import DATA                                            # noqa: E402

RUN_LOG = DATA / "auto_worklist_log.jsonl"   # one line per run; Task Scheduler eats stdout
COUNT = 5
SKIP_BUCKETS = {"1_KILL"}


def eligible(offers):
    """The offers that qualify, best score first."""
    live = [o for o in offers if not o["archived"]]
    # Grouped by identity key, not display name: "Netia" and "NETIA S.A." are one employer and
    # would otherwise both look like lone postings.
    per_company = collections.Counter(o["company_key"] for o in live)
    cands = [o for o in live
             if o["applied_by"] is None
             and per_company[o["company_key"]] == 1
             and o["bucket_name"] not in SKIP_BUCKETS]
    # Title breaks ties so the same run twice picks the same five.
    cands.sort(key=lambda o: (-o["score"], o["title"]))
    return cands


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", "--count", type=int, default=COUNT, help=f"offers to pick ({COUNT})")
    ap.add_argument("--dry-run", action="store_true", help="print the picks, write nothing")
    args = ap.parse_args()

    at = datetime.now(timezone.utc).isoformat()
    cands = eligible(api_offers()["offers"])
    picked = cands[:args.count]

    print(f"{at}  {len(cands)} eligible, picking {len(picked)}")
    for o in picked:
        print(f"  {o['score']:+3d} {o['bucket_name']:9} {o['company'][:38]:38} {o['title'][:50]}")
    if len(picked) < args.count:
        # Not an error: the pool genuinely runs dry as you apply. Worth seeing in the log.
        print(f"  ! only {len(picked)} offers qualify (wanted {args.count})")

    if args.dry_run:
        print("dry run — worklist.json untouched")
        return

    res = api_worklist(WorklistBody(urls=[o["url"] for o in picked]))
    print(f"wrote {res['written']} -> {WORKLIST}")

    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOG.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"at": at, "eligible": len(cands), "written": res["written"],
                            "offers": [{"url": o["url"], "title": o["title"],
                                        "company": o["company"], "score": o["score"]}
                                       for o in picked]}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
