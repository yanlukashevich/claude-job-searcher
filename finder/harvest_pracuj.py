"""Fetch all junior+mid IT offers from pracuj.pl into the same offers_db.jsonl.

pracuj has a real backend API (`POST massachusetts.pracuj.pl/jobOffers/listing/grouped`) but
it answers 401 to anonymous callers, so we take the front door instead: every listing page
ships the server's own answer to that call embedded in its `__NEXT_DATA__` blob. Same fields,
same counts, no auth. `?pn=` pages it and `?rop=` sets the page size (200 is honoured).

Two passes, because the plain feed carries no category and the cockpit needs one:
  1. once per IT specialization (`&its=backend`, ...) -- the specialization IS the category;
  2. once over the plain feed, to pick up offers pracuj's own taxonomy never placed
     (category `it-other`). Skipping this pass would silently drop them.

Rows land in the shape harvest.py writes, and `offer_id` ignores the site, so a job posted on
both portals collapses into one record carrying both links. See finder/README.md.

Usage:
  python finder/harvest_pracuj.py
"""
import datetime
import json
import re
import sys
import time

from common import (OFFERS_DB, clean_text, get_html, log_run, merge, offer_id, read_jsonl,
                    union_sources, write_jsonl)

SITE = "pracuj"
BASE = "https://it.pracuj.pl/praca"
LEVELS = "17,4"            # 17 = junior, 4 = mid/regular (pracuj's positionLevels dictionary)
ROP = 200                  # rows per page; the listing honours this, no deep-page cap
MIN_FULL = 1200            # sanity floor -- see harvest.py's MIN_FULL

# The `its` dictionary, verbatim from the page payload. These are pracuj's own IT
# specializations; the code doubles as our category, so they sit alongside justjoin's
# language-shaped categories (net/python/java) rather than replacing them.
SPECS = ["backend", "frontend", "fullstack", "mobile", "architecture", "devops", "gamedev",
         "data-analytics-and-bi", "big-data-science", "embedded", "testing", "security",
         "helpdesk", "product-management", "project-management", "agile", "ux-ui",
         "business-analytics", "system-analytics", "sap-erp", "it-admin", "ai-ml"]

NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
LEVEL_WORDS = {"junior": 0, "mid": 1, "senior": 2}       # sorted lowest-first for display
WORK_MODES = [("zdalna", "remote"), ("hybrydowa", "hybrid"),
              ("stacjonarna", "office"), ("mobilna", "mobile")]


def job_offers(its, pn):
    """One listing page -> the `jobOffers` payload the server rendered into the HTML.

    The blob is their app's internal state, not a published interface: it has already moved
    once (props.pageProps.data.jobOffers -> dehydratedState). So every step that could have
    moved again exits loudly. A silent {} here would look like an empty market and archive
    the whole db.
    """
    url = f"{BASE}?et={LEVELS}&pn={pn}&rop={ROP}" + (f"&its={its}" if its else "")
    m = NEXT_DATA.search(get_html(url))
    if not m:
        sys.exit(f"FATAL: no __NEXT_DATA__ in {url} -- the page shape changed.")
    queries = json.loads(m.group(1))["props"]["pageProps"].get("dehydratedState", {}).get("queries")
    if queries is None:
        sys.exit(f"FATAL: no dehydratedState.queries in {url} -- the payload moved again.")
    for q in queries:
        k = q.get("queryKey")
        if isinstance(k, list) and k and k[0] == "jobOffers":
            return q["state"]["data"]
    sys.exit(f"FATAL: no 'jobOffers' query in {url} -- the payload moved again.")


def pages(its=None):
    """Every grouped offer for one filter. Paginates on groupedOffersTotalCount: the *other*
    count (offersTotalCount) counts each city copy separately and would page ~20 times past
    the end, then report a permanent phantom shortfall."""
    pn, seen, total = 1, 0, None
    while True:
        data = job_offers(its, pn)
        batch = data.get("groupedOffers") or []
        if total is None:
            total = data["groupedOffersTotalCount"]
        yield from batch
        seen += len(batch)
        if not batch or seen >= total:
            return
        pn += 1
        time.sleep(0.2)


def level_of(position_levels):
    """['Młodszy specjalista / Młodsza specjalistka (junior)'] -> 'junior'. The level is a
    Polish sentence; only the English parenthetical is stable, so that is what we read. An
    offer can list several, and does: '(junior)' + '(mid / Regular)' -> 'junior/mid'."""
    found = set()
    for s in position_levels or []:
        m = re.search(r"\(([^)]*)\)", s)
        for w in LEVEL_WORDS:
            if m and w in m.group(1).lower():
                found.add(w)
    return "/".join(sorted(found, key=LEVEL_WORDS.get)) or "?"


def workplace_of(work_modes):
    out = [en for s in work_modes or [] for pl, en in WORK_MODES if pl in s.lower()]
    return "/".join(dict.fromkeys(out)) or "?"


def cities_of(offers):
    """displayWorkplace is 'Warszawa, Wola' -- city plus district. Keep the city; the district
    would otherwise read as a second location once the cities are joined for the worklist."""
    out = []
    for o in offers or []:
        if o.get("isWholePoland"):
            out.append("Cała Polska")
        w = (o.get("displayWorkplace") or "").split(",")[0].strip()
        if w:
            out.append(w)
    return sorted(set(out))


def to_row(g, category):
    title, company = clean_text(g["jobTitle"]), clean_text(g["companyName"])
    oid = offer_id(title, company)
    offers = g.get("offers") or []
    return {
        "id": oid,
        "title": title,
        "company": company,
        "category": category,
        "level": level_of(g.get("positionLevels")),
        "skills": [t for t in (g.get("technologies") or []) if isinstance(t, str)],
        "salary": g.get("salaryDisplayText") or "?",
        "workplace": workplace_of(g.get("workModes")),
        "cities": cities_of(offers),
        # pracuj publishes no analog of justjoin's applyMethod. isOneClickApply is the only
        # apply signal it gives, and it is not the same question, so it gets its own field
        # and apply_method stays empty = unknown.
        "apply_method": "",
        "apply_url": "",
        "one_click": bool(g.get("isOneClickApply")),
        "published": g.get("lastPublicated"),
        "expires": g.get("expirationDate"),
        "first_seen": datetime.date.today().isoformat(),
        "sources": [{"site": SITE, "slug": str(g.get("groupId") or ""),
                     "url": (offers[0].get("offerAbsoluteUri") if offers else "")}],
    }


def collapse_into(by_id, row):
    """One record per title+company, cities unioned -- the same collapse harvest.py does.

    pracuj groups a job's cities inside one groupId, but a job advertised in several cities is
    *also* published as several groups (own groupId, own URL, own city each), so grouping
    server-side is not enough. Keeping only the first would apply to one city and silently
    hide the rest. The same union also runs across passes, since an offer can sit in two
    specializations; the earlier pass keeps the category."""
    cur = by_id.get(row["id"])
    if cur is None:
        by_id[row["id"]] = row
        return
    cur["cities"] = sorted(set(cur["cities"]) | set(row["cities"]))
    union_sources(cur, row["sources"])


def fetch_fresh():
    """The whole pracuj harvest as {id: offer}. Specializations first so their category
    sticks; the plain sweep then only fills in what no specialization claimed."""
    by_id = {}
    for spec in SPECS:
        n = 0
        for g in pages(spec):
            collapse_into(by_id, to_row(g, spec))
            n += 1
        print(f"  {spec:24} {n:5}")
    labelled = len(by_id)
    n = 0
    for g in pages(None):
        collapse_into(by_id, to_row(g, "it-other"))
        n += 1
    print(f"  {'(plain feed)':24} {n:5}  -> {len(by_id) - labelled} outside every specialization")
    if len(by_id) < MIN_FULL:
        sys.exit(f"FATAL: harvest returned only {len(by_id)} offers (expected >{MIN_FULL}). "
                 f"Refusing to merge -- archiving on a broken fetch would expire the whole db.")
    return by_id


def main():
    fresh = fetch_fresh()
    print(f"pracuj: {len(fresh)} unique offers")

    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    merged, s = merge(read_jsonl(OFFERS_DB), [(SITE, fresh)], at)
    write_jsonl(OFFERS_DB, merged)
    log_run(s)
    print(f"offers_db: +{s['added']} new, {s['linked']} also on justjoin, "
          f"{s['archived']} archived, {s['revived']} revived, "
          f"{s['total']} total ({s['archived_total']} archived)")
    print("next: python finder/app.py")


if __name__ == "__main__":
    main()
