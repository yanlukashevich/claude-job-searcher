"""Re-key offers_db.jsonl with the current offer_id and fold the duplicates together.

The stored rows carry the id that `offer_id` produced on the day they were harvested. Change
the normalizer -- or edit company_aliases.json -- and the rows already on disk keep their old
ids, so the fix only ever applies to offers harvested afterwards. This script closes that gap:
it recomputes every id and merges the rows that now collide.

Merging is not a matter of keeping one row. Two portals describe the same job differently and
each knows something the other does not (justjoin has the salary and the apply method, pracuj
has the expiry date), so every field has its own rule below.

Dry run by default -- it prints what it would merge and touches nothing.

Usage:
  python finder/migrate_offer_ids.py            # show the clusters
  python finder/migrate_offer_ids.py --apply    # back up, then rewrite the db
"""
import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (DATA, OFFERS_DB, ROOT, clean_text, offer_id,  # noqa: E402
                    read_jsonl, write_jsonl)

MANUAL = DATA / "manual_applied.json"
LOG = ROOT / "src" / "applications_log.jsonl"

EMPTY = ("", "?", None)


def _first(rows, field):
    for r in rows:
        if r.get(field) not in EMPTY:
            return r.get(field)
    return rows[0].get(field)


def _union(rows, field):
    out = set()
    for r in rows:
        out |= {x for x in (r.get(field) or []) if x}
    return sorted(out)


def _extreme(rows, field, newest):
    vals = [r.get(field) for r in rows if r.get(field)]
    if not vals:
        return None
    return max(vals) if newest else min(vals)


def _filled(row):
    return sum(1 for f in ("salary", "level", "workplace", "category", "apply_method",
                           "published", "expires") if row.get(f) not in EMPTY)


def merge_rows(rows, new_id):
    """Fold every row that now shares an id into one. `rows` is never empty."""
    # The base decides title/company spelling and anything with no better rule: the row that
    # knows the most about the job, and among equals the one seen first.
    rows = sorted(rows, key=lambda r: (-_filled(r), r.get("first_seen") or "9999"))
    base = rows[0]

    out = dict(base)
    out["id"] = new_id
    out["title"] = clean_text(base.get("title", ""))
    out["company"] = clean_text(base.get("company", ""))
    for field in ("salary", "level", "workplace", "apply_method", "apply_url"):
        out[field] = _first(rows, field)
    # "it-other" is pracuj's bucket for what its taxonomy could not place -- a real category
    # from the other portal beats it.
    out["category"] = next((r["category"] for r in rows
                            if r.get("category") not in EMPTY + ("it-other",)),
                           _first(rows, "category"))
    out["skills"] = _union(rows, "skills")
    out["cities"] = _union(rows, "cities")
    out["one_click"] = any(r.get("one_click") for r in rows)

    # Dates: when you FIRST saw the job (the earliest of the copies) and the freshest thing
    # either portal says about it.
    for field, newest in (("first_seen", False), ("added_at", False),
                          ("published", True), ("expires", True), ("revived_at", True)):
        v = _extreme(rows, field, newest)
        if v:
            out[field] = v
        else:
            out.pop(field, None)

    srcs, seen = [], set()
    for r in rows:
        for s in r.get("sources") or []:
            if s.get("url") not in seen:
                seen.add(s.get("url"))
                srcs.append(dict(s))
    out["sources"] = srcs

    # An offer is expired only once every link to it is. Recomputed rather than carried over:
    # merging an archived row into a live one has to yield a live offer.
    stamps = [s.get("archived_at") for s in srcs]
    if srcs and all(stamps):
        out["archived_at"] = max(stamps)
    else:
        out.pop("archived_at", None)
    return out


def applied_urls():
    """Every URL you have already applied through -- bot log plus your manual marks."""
    urls = set()
    if LOG.exists():
        for row in read_jsonl(LOG):
            if row.get("url"):
                urls.add(row["url"])
    if MANUAL.exists():
        urls |= set(json.loads(MANUAL.read_text(encoding="utf-8")))
    return urls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="rewrite the db (default: dry run)")
    ap.add_argument("--show", type=int, default=15, help="how many clusters to print")
    args = ap.parse_args()

    rows = read_jsonl(OFFERS_DB)
    if not rows:
        sys.exit(f"{OFFERS_DB} is empty or missing -- nothing to migrate.")

    groups = {}
    for r in rows:
        oid = offer_id(r.get("title", ""), r.get("company", ""))
        groups.setdefault(oid, []).append(r)
    clusters = {k: v for k, v in groups.items() if len(v) > 1}

    print(f"{len(rows)} rows -> {len(groups)} offers "
          f"({len(rows) - len(groups)} duplicates folded into {len(clusters)} offers)")
    cross = sum(1 for v in clusters.values()
                if len({s.get("site") for r in v for s in r.get("sources") or []}) > 1)
    print(f"  {cross} of those clusters span both portals -- links that were never joined")
    renamed = sum(1 for r in rows if clean_text(r.get("title", "")) != r.get("title", "")
                  or clean_text(r.get("company", "")) != r.get("company", ""))
    print(f"  {renamed} rows have invisible characters or odd spacing cleaned out of "
          f"title/company")

    for v in list(clusters.values())[:args.show]:
        print("  --")
        for r in v:
            sites = "".join(sorted((s.get("site") or "?")[0] for s in r.get("sources") or []))
            print(f"     {sites:3} {r.get('company','')!r} | {r.get('title','')!r}")
    if len(clusters) > args.show:
        print(f"  ... and {len(clusters) - args.show} more (--show N to see them)")

    merged = [merge_rows(v, k) for k, v in groups.items()]

    # The one thing a merge must never do: lose a link you already applied through, because a
    # row that no longer answers to that URL reads as "not applied" and gets applied twice.
    kept = {s.get("url") for r in merged for s in r.get("sources") or []}
    before = {s.get("url") for r in rows for s in r.get("sources") or []}
    lost = (before - kept) & applied_urls()
    print(f"\nURLs: {len(before)} before, {len(kept)} after, "
          f"{len(lost)} applied-through URLs would be lost")
    if lost:
        sys.exit("REFUSING: the merge would drop URLs you have applied through:\n  "
                 + "\n  ".join(sorted(lost)))

    if not args.apply:
        print("\ndry run -- nothing written. Re-run with --apply to rewrite the db.")
        return

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = OFFERS_DB.with_suffix(f".jsonl.bak-{stamp}")
    shutil.copy2(OFFERS_DB, backup)
    write_jsonl(OFFERS_DB, merged)
    print(f"\nwrote {len(merged)} rows to {OFFERS_DB.name} (backup: {backup.name})")


if __name__ == "__main__":
    main()
