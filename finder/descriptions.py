"""Download each offer's own text -- the duties and requirements the listing pages never carry.

The listing feeds give title, company, skills and salary; everything a person actually reads
lives on the offer's own page, one request per offer. So this runs as a slow background pass,
started by the cockpit after a harvest (finder/app.py's /api/harvest) and never next to the
23:00 applier: it waits for the harvest's burst to cool down, walks the new offers best score
first, and pauses a few seconds between requests. Cut it short at any point and the offers you
care about are the ones already done.

Two portals, two shapes:
  justjoin  a public per-offer API whose `body` is a small HTML fragment  (~9 KB of JSON)
  pracuj    the offer page's __NEXT_DATA__ blob, already split into typed sections (~400 KB)
justjoin is tried first when an offer has both -- same text, a fortieth of the bytes.

Stopping is the whole safety model. A 403/429 from either portal, three other errors in a row,
the cap, or the clock reaching 22:30 ends the run immediately; whatever it did not reach is
simply picked up after the next harvest. Nothing is ever re-downloaded: one line per offer in
data/descriptions.jsonl, appended, and a `gone` offer counts as answered.

Usage:
  python finder/descriptions.py                 # run now, no wait
  python finder/descriptions.py --delay 600     # what the cockpit starts after a harvest
  python finder/descriptions.py --cap 0         # just print how many offers are pending
  python finder/descriptions.py --url URL       # one offer, now
"""
import argparse
import datetime
import json
import random
import sys
import time
import urllib.error
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                    # common, harvest_pracuj
sys.path.insert(0, str(HERE / "prototype"))      # scoring

from common import (DATA, OFFERS_DB, append_jsonl, get_html,   # noqa: E402
                    get_json, read_jsonl, write_json)
from harvest_pracuj import NEXT_DATA              # noqa: E402
from scoring import classify                      # noqa: E402

DESC_DB = DATA / "descriptions.jsonl"            # one line per offer, append-only, last wins
RUN_STATE = DATA / "descriptions_run.json"       # what the run is doing, for the harvest page

FRESH_DAYS = 7            # older offers are fetched one at a time from the cockpit, not in bulk
CAP = 300                 # a run never makes more requests than this
STOP_AT = (22, 30)        # local time; the nightly applier gets the IP to itself from here
PAUSE = (2.0, 6.0)        # seconds between requests -- about the pace of a person reading
MAX_ERRORS = 3            # consecutive failures that are not a block: something is wrong, stop
# A killed or vetoed offer is one you will never open, so its description is pure request budget
# spent on nothing. This is the only filter -- everything else new gets fetched.
SKIP_BUCKETS = {"1_KILL", "2_VETO"}

JJ_OFFER = "https://justjoin.it/api/candidate-api/offers/{}"
# pracuj serves a page for every /praca/...,oferta,<id> URL it ever had; an offer that is gone
# gets the generic listing instead, and __NEXT_DATA__.page is what says which of the two you
# are holding. Without this check every expired offer would look like a payload that moved.
PRACUJ_OFFER_PAGE = "/offerview"


class Blocked(Exception):
    """A portal answered 403/429. Not an error to retry -- a request to stop asking."""


class ShapeChanged(Exception):
    """The payload no longer holds the text where it did. Stop loudly: saving thousands of
    empty descriptions would be indistinguishable from a market with no job descriptions."""


# ---- justjoin: an HTML fragment ------------------------------------------------------------

class _Text(HTMLParser):
    """justjoin's `body` is editor HTML: paragraphs, bullet lists, bold. Only two things in it
    carry meaning -- where the lines break, and which of them are bullets -- so every
    block-level tag ends the current line and everything else is dropped. No tags, no
    attributes and no styling ever reach the cockpit or a future prompt.

    Lines come out as (kind, text), kind being "li" or "p": a requirements list read as one
    grey paragraph is the part of the offer you actually came to read."""

    BREAKS = {"li", "p", "br", "div", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self._buf, self._li = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.BREAKS:
            self._flush()
        if tag == "li":
            self._li += 1                     # a <p> inside an <li> is still a bullet

    def handle_endtag(self, tag):
        if tag in self.BREAKS:
            self._flush()
        if tag == "li":
            self._li = max(0, self._li - 1)

    def handle_data(self, data):
        self._buf.append(data)

    def _flush(self):
        line = " ".join("".join(self._buf).split())
        if line:
            self.lines.append(("li" if self._li else "p", line))
        self._buf = []

    def close(self):
        super().close()
        self._flush()


def body_sections(html):
    """An offer body -> the same [{type, items}] shape pracuj hands over, so the cockpit has one
    renderer and not two. Runs of bullets become a `bullets` section, prose a `description` one;
    neither is titled, because justjoin's body carries no headings of its own."""
    p = _Text()
    p.feed(html or "")
    p.close()
    out = []
    for kind, line in p.lines:
        want = "bullets" if kind == "li" else "description"
        if not out or out[-1]["type"] != want:
            out.append({"type": want, "items": []})
        out[-1]["items"].append(line)
    return out


def _justjoin(slug):
    data = get_json(JJ_OFFER.format(slug))
    return body_sections(data.get("body"))


# ---- pracuj: a JSON blob inside the page ---------------------------------------------------

def _find_key(obj, key):
    """The first value stored under `key`, wherever it sits. The blob is pracuj's own app state
    and has already moved once (harvest_pracuj.job_offers tells that story), so the text is
    found by name rather than by path -- a path breaks on the next move, a name does not."""
    stack = [obj]
    while stack:
        cur = stack.pop(0)
        if isinstance(cur, dict):
            if key in cur:
                return cur[key]
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return None


def _pracuj(url):
    """The offer's sections, or None if pracuj no longer has this offer."""
    m = NEXT_DATA.search(get_html(url))
    if not m:
        raise ShapeChanged(f"no __NEXT_DATA__ in {url}")
    blob = json.loads(m.group(1))
    if blob.get("page") != PRACUJ_OFFER_PAGE:
        return None                       # served the listing: this offer is not there any more
    sections = _find_key(blob, "textSections")
    if sections is None:
        raise ShapeChanged(f"no textSections in {url} -- the payload moved again")
    out = []
    for s in sections:
        items = [t for t in (s.get("textElements") or []) if isinstance(t, str) and t.strip()]
        if items:
            out.append({"type": s.get("sectionType") or "description", "items": items})
    return out


# ---- one offer -----------------------------------------------------------------------------

SITE_OF = [("justjoin.it", "justjoin"), ("pracuj.pl", "pracuj")]


def site_of(url):
    return next((site for host, site in SITE_OF if host in (url or "")), "")


def pick_source(offer):
    """Which link to fetch. justjoin before pracuj -- 9 KB of JSON against 400 KB of HTML for
    the same text -- and a live link before an archived one, which is the only one worth asking
    about anyway."""
    srcs = [s for s in offer.get("sources", []) if s.get("url")]
    order = {"justjoin": 0, "pracuj": 1}
    srcs.sort(key=lambda s: (bool(s.get("archived_at")),
                             order.get(s.get("site") or site_of(s["url"]), 9)))
    return srcs[0] if srcs else None


def fetch_one(offer):
    """One offer -> one descriptions.jsonl record. Raises Blocked / ShapeChanged; every other
    HTTP failure propagates, and the caller counts it."""
    src = pick_source(offer)
    if src is None:
        raise ValueError(f"offer {offer.get('id')} has no link to fetch")
    url = src["url"]
    site = src.get("site") or site_of(url)
    rec = {"id": offer.get("id"), "site": site, "url": url,
           "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    try:
        if site == "justjoin":
            slug = src.get("slug") or url.rstrip("/").rsplit("/", 1)[-1]
            sections = _justjoin(slug)
        elif site == "pracuj":
            sections = _pracuj(url)
        else:
            raise ValueError(f"no reader for {url}")
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise Blocked(f"{site} answered {e.code}")
        if e.code in (404, 410):
            return {**rec, "status": "gone", "sections": []}
        raise
    if sections is None:
        return {**rec, "status": "gone", "sections": []}
    return {**rec, "status": "ok", "sections": sections}


# ---- the to-do list ------------------------------------------------------------------------

def have():
    """{offer id: status} from descriptions.jsonl. A `gone` offer counts as answered -- asking
    again every night for an offer the portal has deleted is exactly the traffic to avoid."""
    return {r["id"]: r.get("status") for r in read_jsonl(DESC_DB) if r.get("id")}


def candidates(rows=None):
    """What to fetch, best score first. Only what the last week's harvests brought in and the
    keyword filter kept: old offers are fetched one at a time from the cockpit's button, and a
    killed one is never opened."""
    rows = read_jsonl(OFFERS_DB) if rows is None else rows
    done = have()
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=FRESH_DAYS)).isoformat()
    out = []
    for o in rows:
        if o.get("archived_at") or o["id"] in done:
            continue
        if not o.get("added_at") or o["added_at"] < cutoff:
            continue
        bucket, score, _ = classify(o)
        if bucket in SKIP_BUCKETS:
            continue
        out.append((score, o))
    # Best first, so a run that is cut short by a block or by the clock has already fetched the
    # offers you would actually have opened.
    out.sort(key=lambda p: -p[0])
    return [o for _, o in out]


# ---- the run -------------------------------------------------------------------------------

def _state(**fields):
    write_json(RUN_STATE, fields)


def _past_stop():
    now = datetime.datetime.now()
    return (now.hour, now.minute) >= STOP_AT


def run(delay=0, cap=CAP):
    """Wait, then walk the to-do list one offer at a time. Returns the final state dict.

    The candidates are computed AFTER the wait, so a second harvest while this one is sleeping
    is covered by the run already scheduled instead of needing one of its own."""
    starts = datetime.datetime.now() + datetime.timedelta(seconds=delay)
    base = {"starts_at": starts.astimezone().isoformat(timespec="seconds"),
            "total": None, "ok": 0, "gone": 0, "reason": None}
    if delay:
        _state(state="waiting", **base)
        print(f"waiting {delay}s -- starts {starts:%H:%M}", flush=True)
        time.sleep(delay)
    todo = candidates()[:cap]
    base["total"] = len(todo)
    _state(state="running", **base)
    print(f"{len(todo)} offer(s) to fetch", flush=True)
    ok = gone = errors = 0
    reason = None
    for i, offer in enumerate(todo, 1):
        if _past_stop():
            reason = f"stopped at {STOP_AT[0]:02d}:{STOP_AT[1]:02d} -- the nightly run is next"
            break
        try:
            rec = fetch_one(offer)
        except Blocked as e:
            reason = f"{e} -- continues after the next harvest"
            break
        except ShapeChanged as e:
            reason = f"the payload changed: {e}"
            break
        except Exception as e:                    # a timeout, a 500, a page that will not parse
            errors += 1
            print(f"  {i:4}/{len(todo)} ERROR {type(e).__name__}: {e}", flush=True)
            if errors >= MAX_ERRORS:
                reason = f"{errors} errors in a row, last: {e}"
                break
            time.sleep(random.uniform(*PAUSE))
            continue
        errors = 0
        append_jsonl(DESC_DB, [rec])
        ok += rec["status"] == "ok"
        gone += rec["status"] == "gone"
        base.update(ok=ok, gone=gone)
        _state(state="running", **base)
        print(f"  {i:4}/{len(todo)} {rec['status']:4} {rec['site']:8} "
              f"{offer.get('title', '')[:60]}", flush=True)
        if i < len(todo):
            time.sleep(random.uniform(*PAUSE))
    base["reason"] = reason
    final = dict(base, state="stopped" if reason else "done")
    _state(**final)
    print(f"done: {ok} saved, {gone} gone" + (f" -- {reason}" if reason else ""), flush=True)
    return final


def one_url(url):
    """Fetch the offer owning `url`. A link the db does not know still works -- the site and the
    slug are both readable off the URL."""
    offer = next((o for o in read_jsonl(OFFERS_DB)
                  if any(s.get("url") == url for s in o.get("sources", []))), None)
    if offer is None:
        offer = {"id": url, "sources": [{"site": site_of(url), "url": url}]}
    rec = fetch_one(offer)
    append_jsonl(DESC_DB, [rec])
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--delay", type=int, default=0, help="seconds to wait before starting")
    ap.add_argument("--cap", type=int, default=CAP, help="most offers to fetch (0 = just count)")
    ap.add_argument("--url", help="fetch this one offer now and exit")
    args = ap.parse_args()

    if args.url:
        rec = one_url(args.url)
        n = sum(len(s["items"]) for s in rec["sections"])
        print(f"{rec['status']} · {rec['site']} · {len(rec['sections'])} section(s), {n} line(s)")
        return
    if args.cap == 0:
        print(f"{len(candidates())} offer(s) pending")
        return
    run(args.delay, args.cap)


if __name__ == "__main__":
    main()
