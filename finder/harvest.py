"""Fetch all junior+mid offers from justjoin.it into offers_db.jsonl.

- Pages through the public list API (itemsCount=100 is honored; `from` paginates, cursor lies).
- Collapses per-city duplicates on title+company; the feed is publishedAt-desc so the
  kept row is the newest.
- Upserts: new ids are appended, known ids keep their stored row.
- An offer is never deleted. One that fell off the feed gets `archived_at` stamped (expired);
  one that comes back has it cleared. The cockpit hides archived offers by default.

This is the only data source the triage prototype (finder/prototype/) reads.

Usage:
  python finder/harvest.py            # full harvest: adds new, archives what's gone
  python finder/harvest.py --days 7   # weekly run: stop paging past the cutoff (adds only)
"""
import argparse
import datetime
import sys
import time

from common import (OFFERS_DB, clean_text, get_json, log_run, merge, offer_id, read_jsonl,
                    salary_str, union_sources, write_jsonl)

SITE = "justjoin"
LIST_URL = ("https://justjoin.it/api/candidate-api/offers"
            "?experienceLevels=mid&experienceLevels=junior"
            "&sortBy=publishedAt&orderBy=descending")

# A full harvest is what licenses archiving, so a full harvest that comes back near-empty
# would stamp `archived_at` on the whole db while printing a perfectly normal summary. The
# feed has never been below ~3000; anything under this is a broken fetch, not a dead market.
MIN_FULL = 1500


def fetch_rows(days):
    cutoff = None
    if days:
        cutoff = (datetime.datetime.now(datetime.timezone.utc)
                  - datetime.timedelta(days=days)).isoformat()
    rows, frm = [], 0
    while True:
        page = get_json(f"{LIST_URL}&from={frm}&itemsCount=100")
        rows += page["data"]
        frm += 100
        if frm >= page["meta"]["totalItems"]:
            break
        # Promoted rows can sit slightly out of order, so only stop once the
        # whole page is older than the cutoff, and filter exact rows later.
        if cutoff and all(r["publishedAt"] < cutoff for r in page["data"]):
            break
        time.sleep(0.15)
    if cutoff:
        rows = [r for r in rows if r["publishedAt"] >= cutoff]
    return rows


def collapse(rows):
    """One record per title+company; union the cities and links of every collapsed copy."""
    by_id = {}
    for r in rows:
        title, company = clean_text(r["title"]), clean_text(r["companyName"])
        oid = offer_id(title, company)
        cities = [l["city"] for l in (r.get("locations") or [])] or [r.get("city", "")]
        src = {"site": SITE, "slug": r["slug"],
               "url": f"https://justjoin.it/job-offer/{r['slug']}"}
        if oid in by_id:
            o = by_id[oid]
            o["cities"] = sorted(set(o["cities"]) | set(cities))
            # not only per-city copies land here: two spellings of one title collapse too, and
            # those are separate postings with separate apply links. Keep both.
            union_sources(o, [src])
            continue
        by_id[oid] = {
            "id": oid,
            "title": title,
            "company": company,
            "category": r["category"]["key"],
            "level": r["experienceLevel"],
            "skills": [s["name"] for s in (r.get("requiredSkills") or [])],
            "salary": salary_str(r.get("employmentTypes")),
            "workplace": r.get("workplaceType", "?"),
            "cities": sorted(set(c for c in cities if c)),
            "apply_method": r.get("applyMethod"),
            "apply_url": r.get("applyUrl"),
            "published": r.get("publishedAt"),
            "first_seen": datetime.date.today().isoformat(),
            "sources": [src],
        }
    return by_id


def fetch_fresh(days=0):
    """The whole harvest as {id: offer}, ready to merge. Used by main() and by the
    cockpit's Re-harvest button (finder/app.py) so both share one code path."""
    fresh = collapse(fetch_rows(days))
    if not days and len(fresh) < MIN_FULL:
        sys.exit(f"FATAL: full harvest returned only {len(fresh)} offers (expected >{MIN_FULL}). "
                 f"Refusing to merge -- archiving on a broken fetch would expire the whole db.")
    return fresh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0,
                    help="only offers published in the last N days (0 = everything)")
    args = ap.parse_args()

    fresh = fetch_fresh(args.days)
    print(f"justjoin: {len(fresh)} unique offers")

    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    merged, s = merge(read_jsonl(OFFERS_DB), [(SITE, fresh)], at,
                      archive_missing=not args.days)
    write_jsonl(OFFERS_DB, merged)
    log_run(s)
    print(f"offers_db: +{s['added']} new, {s['linked']} also on another portal, "
          f"{s['archived']} archived, {s['revived']} revived, "
          f"{s['total']} total ({s['archived_total']} archived)")
    if args.days:
        print("(--days is a partial feed: nothing archived)")
    print("next: python finder/harvest_pracuj.py, then python finder/app.py")


if __name__ == "__main__":
    main()
