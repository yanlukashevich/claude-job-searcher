"""Fetch all junior+mid offers from justjoin.it into offers_db.jsonl.

- Pages through the public list API (itemsCount=100 is honored; `from` paginates, cursor lies).
- Collapses per-city duplicates on title+company; the feed is publishedAt-desc so the
  kept row is the newest.
- Upserts: known ids are skipped, new ids are appended. Nothing is ever rewritten.

This is the only data source the triage prototype (finder/prototype/) reads.

Usage:
  python finder/harvest.py            # full harvest (first run)
  python finder/harvest.py --days 7   # weekly run: stop paging past the cutoff
"""
import argparse
import datetime
import time

from common import (OFFERS_DB, append_jsonl, get_json, offer_id, read_jsonl,
                    salary_str)

LIST_URL = ("https://justjoin.it/api/candidate-api/offers"
            "?experienceLevels=mid&experienceLevels=junior"
            "&sortBy=publishedAt&orderBy=descending")


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
    """One record per title+company; union the cities of every collapsed copy."""
    by_id = {}
    for r in rows:
        oid = offer_id(r["title"], r["companyName"])
        cities = [l["city"] for l in (r.get("locations") or [])] or [r.get("city", "")]
        if oid in by_id:
            o = by_id[oid]
            o["cities"] = sorted(set(o["cities"]) | set(cities))
            continue
        by_id[oid] = {
            "id": oid,
            "title": r["title"],
            "company": r["companyName"],
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
            "sources": [{"site": "justjoin", "slug": r["slug"],
                         "url": f"https://justjoin.it/job-offer/{r['slug']}"}],
        }
    return by_id


def fetch_fresh(days=0):
    """The whole harvest as {id: offer}, ready to merge. Used by main() and by the
    cockpit's Re-harvest button (finder/app.py) so both share one code path."""
    return collapse(fetch_rows(days))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0,
                    help="only offers published in the last N days (0 = everything)")
    args = ap.parse_args()

    rows = fetch_rows(args.days)
    fresh = collapse(rows)
    print(f"fetched {len(rows)} rows -> {len(fresh)} unique offers")

    known = {o["id"] for o in read_jsonl(OFFERS_DB)}
    new = [o for o in fresh.values() if o["id"] not in known]
    append_jsonl(OFFERS_DB, new)
    print(f"offers_db: {len(known)} known, +{len(new)} new, {len(known) + len(new)} total")
    print("next: python finder/prototype/browse.py --open")


if __name__ == "__main__":
    main()
