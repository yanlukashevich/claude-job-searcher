"""One page, one source of truth. The apply cockpit.

Serves offers.html and a tiny JSON API that JOINS four files by offer URL:
  - finder/data/offers_db.jsonl   the offers (harvest.py writes it; rows are never deleted,
                                  vanished ones are stamped archived_at)
  - runner/data/applications_log.jsonl   what the BOT did (run_batch.py appends; append-only)
  - finder/data/manual_applied.json   what YOU did by hand (mutable, toggle-able)
  - runner/data/worklist.json     the apply QUEUE, which the nightly runner drains
and serves the outreach cards (finder/data/dig_deeper.json, rules in outreach.py) to /outreach.

The two write patterns are different on purpose. Automated runs append to the JSONL log
(crash-safe, no read-modify-write). Your manual marks are one interactive click, so they live
in a plain mutable dict you can toggle on and off -- you cannot un-append a JSONL line.

The queue is a third pattern again: run_batch.py deletes from the same file while you are
clicking in it, so every write here is read-modify-write onto a temp file plus os.replace.
A whole-file overwrite from a stale in-memory copy would erase whatever the other side did.

Run:
  python finder/app.py            # http://127.0.0.1:9000
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent           # finder/
sys.path.insert(0, str(HERE))                    # common
sys.path.insert(0, str(HERE / "prototype"))      # scoring, keywords
sys.path.insert(0, str(HERE.parent / "runner"))  # stats (run diagnostics)

from common import (ROOT, HARVEST_LOG, LAST_HARVEST,   # noqa: E402
                    canonical_names, log_run, merge, norm_company, write_json, write_jsonl)
from scoring import classify, BUCKETS            # noqa: E402
import stats                                     # noqa: E402  runner/stats.py
import harvest                                    # noqa: E402  justjoin
import harvest_pracuj                             # noqa: E402  pracuj.pl
# The outreach list, finder/data/dig_deeper.json: offers you also chase by hand, one card each
# with its contacts and email draft. Deliberately in finder/data/, not src/ -- the applier must
# never pay tokens for it. The card rules live in outreach.py, shared with send_outreach.py.
import outreach                                   # noqa: E402
import send_outreach                              # noqa: E402  the /outreach Send button

OFFERS_DB = HERE / "data" / "offers_db.jsonl"
MANUAL = HERE / "data" / "manual_applied.json"
MANUAL_SCORES = HERE / "data" / "manual_scores.json"   # url -> {score, reason, at} (your overrides)
LOG = ROOT / "runner" / "data" / "applications_log.jsonl"
WORKLIST = ROOT / "runner" / "data" / "worklist.json"
BATCH_LOG = ROOT / "runner" / "data" / "batch_log.jsonl"   # one line per nightly batch

# What the nightly task takes off the queue in one go. Shown in the panel so you can see which
# picks run tonight and which wait; register_nightly.ps1 -Count is the value that actually runs.
NIGHTLY_COUNT = 10
PAGE = HERE / "page.html"
HARVEST_PAGE = HERE / "harvest.html"
HISTORY_PAGE = HERE / "history.html"
OUTREACH_PAGE = HERE / "outreach.html"

# offer category (finder taxonomy) -> CV variant stack (profile.md CV-variants table).
# Anything not listed falls through to "universal", which is also the applier's default.
# This is a HINT, not the decision: the applier picks the CV from the offer description it is
# already reading (playbook §7). Only justjoin's categories are language-shaped, so every
# pracuj offer lands on "universal" here -- including its Python and .NET ones.
STACK = {"net": "dotnet", "python": "python", "devops": "cloud/devops"}

app = FastAPI()
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


# ---- readers -------------------------------------------------------------------------------

def _read_jsonl(path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _url_of(offer):
    """The offer's canonical link. An offer carried by both portals has two; prefer one whose
    feed still lists it, so a job that expired on justjoin but is live on pracuj still links
    somewhere you can actually apply."""
    srcs = offer.get("sources", [])
    for s in srcs:
        if s.get("url") and not s.get("archived_at"):
            return s["url"]
    for s in srcs:
        if s.get("url"):
            return s["url"]
    return ""


def _urls_of(offer):
    """Every link this offer has ever had, canonical one first.

    Applied-status is recorded per URL, and one offer can hold several: two portals, or one
    portal that re-posted the job under a new slug. Asking about the canonical link alone
    means an application filed through any of the others stops counting, and the offer comes
    back up for triage as if it were untouched."""
    urls = [s["url"] for s in offer.get("sources", []) if s.get("url")]
    canon = _url_of(offer)
    return [canon] + [u for u in urls if u != canon] if canon else urls


SITE_LETTER = {"justjoin": "j", "pracuj": "p"}


def _sites_of(offer):
    """['justjoin','pracuj'] -> 'jp'. The per-offer portal marker in the cockpit; two letters
    means the same job was found on both and the two records were collapsed into this one."""
    return "".join(sorted(SITE_LETTER.get(s.get("site"), "?")
                          for s in offer.get("sources", []) if s.get("site")))


# Scoring 3500 offers is regex-heavy, but the db only changes when harvest.py runs. Cache the
# scored rows and rebuild only when the file's mtime moves. The log and manual marks are tiny
# and change often (every bot run, every click), so those are re-read on every request.
_cache = {"mtime": None, "offers": None}


def _scored_offers():
    mtime = OFFERS_DB.stat().st_mtime if OFFERS_DB.exists() else 0
    if _cache["mtime"] == mtime:
        return _cache["offers"]
    rows = _read_jsonl(OFFERS_DB)
    # One employer is spelled several ways across (and within) the portals. Group and label by
    # the identity key's canonical spelling, or "Netia" and "NETIA S.A." head two groups.
    display = canonical_names(rows)
    offers = []
    for o in rows:
        bucket, score, why = classify(o)
        cat = o.get("category", "?")
        ckey = norm_company(o.get("company", ""))
        offers.append({
            "url": _url_of(o),
            "urls": _urls_of(o),             # every link — what applied-status is joined on
            "sites": _sites_of(o),           # 'j' / 'p' / 'jp' — which portals carry it
            "sources": o.get("sources", []),  # both links, listed in the detail panel
            "title": o.get("title", ""),
            "company": display.get(ckey) or o.get("company", ""),
            "company_key": ckey,
            "category": cat,
            "stack": STACK.get(cat, "universal"),
            "level": o.get("level", ""),
            "workplace": o.get("workplace", ""),
            "cities": o.get("cities", []),
            "salary": o.get("salary", ""),
            "skills": o.get("skills", []),
            "apply_method": o.get("apply_method", ""),
            "apply_url": o.get("apply_url", ""),
            "published": o.get("published", ""),
            "added_at": o.get("added_at"),   # set by /api/harvest for offers seen in that run
            # archived_at = the run that first found this offer gone from the feed (expired).
            # It is data, not a filter: the cockpit decides whether to show these.
            "archived_at": o.get("archived_at"),
            "revived_at": o.get("revived_at"),
            "score": score,
            "bucket": BUCKETS.index(bucket),
            "bucket_name": bucket,
            "why": why,
        })
    _cache.update(mtime=mtime, offers=offers)
    return offers


def _by_any_url():
    """{any of an offer's URLs: the offer}. Every join onto the offer db goes through this --
    a log line or a manual mark names the link it was filed under, which is not necessarily
    the link the cockpit now shows."""
    idx = {}
    for o in _scored_offers():
        for u in o["urls"]:
            idx.setdefault(u, o)
    return idx


def _offer_urls(url):
    """The sibling links of whatever offer owns `url` (just `url` if none does)."""
    o = _by_any_url().get(url)
    return o["urls"] if o else [url]


def _bot_applications():
    """url -> the LAST log line for that url (a url may be retried; newest outcome wins)."""
    by_url = {}
    for row in _read_jsonl(LOG):
        u = row.get("url")
        if u:
            by_url[u] = row
    return by_url


def _manual():
    if not MANUAL.exists():
        return {}
    return json.loads(MANUAL.read_text(encoding="utf-8"))


def _save_manual(d):
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _manual_scores():
    """url -> {score, reason, at}. Your hand-tuned score overrides; the auto score stays put in
    the db, so clearing this file restores every offer to its computed score."""
    if not MANUAL_SCORES.exists():
        return {}
    return json.loads(MANUAL_SCORES.read_text(encoding="utf-8"))


def _save_manual_scores(d):
    MANUAL_SCORES.parent.mkdir(parents=True, exist_ok=True)
    MANUAL_SCORES.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _queue():
    """The apply queue as it is on disk RIGHT NOW. Always re-read: run_batch.py removes each
    offer the moment it has a log line, so an in-memory copy goes stale within a minute."""
    if not WORKLIST.exists():
        return []
    txt = WORKLIST.read_text(encoding="utf-8").strip()
    return json.loads(txt) if txt else []


def _save_queue(items):
    # atomic (tmp + os.replace): run_batch.py writes worklist.json the same way, for the same
    # reason -- neither side may ever see the other's half-written file.
    write_json(WORKLIST, items)


def _worklist_entry(offer):
    """One queue row, in the exact shape runner/run_batch.py consumes. The single definition:
    the cockpit's clicks and the harvest page's bulk add both come through here, so a row can
    never drift from what the runner expects."""
    return {
        "url": offer["url"],
        "title": offer["title"],
        "company": offer["company"],
        "location": ", ".join(offer["cities"]),
        "stack": offer["stack"],
        "apply_method": offer.get("apply_method", ""),
        "apply_url": offer.get("apply_url", ""),
        "status": "pending",
        "added_at": datetime.now(timezone.utc).isoformat(),
    }


def _last_batch():
    """The last line of runner/data/batch_log.jsonl -- what the nightly run did, or None if it
    has never run. Read on every /api/queue so the panel says whether last night happened."""
    rows = _read_jsonl(BATCH_LOG)
    return rows[-1] if rows else None


def _last_harvest():
    if LAST_HARVEST.exists():
        return json.loads(LAST_HARVEST.read_text(encoding="utf-8"))
    return None


# ---- API -----------------------------------------------------------------------------------

def _enriched_offers():
    """The scored offers with everything the cockpit row needs joined on: manual score
    overrides, bot log lines, manual marks, queue + dig-deeper state, and the is_new flag."""
    bot = _bot_applications()
    manual = _manual()
    scores = _manual_scores()
    queued = {e.get("url") for e in _queue()}
    try:
        dig = outreach.load()
    except outreach.CardsError:
        dig = {}             # the dig panel shows the error; the offer list still has to load
    emailed = {}             # url -> newest time you emailed about it (outreach_sent.jsonl)
    for r in outreach.sent_log():
        if r.get("url") and (r.get("ts") or "") > emailed.get(r["url"], ""):
            emailed[r["url"]] = r.get("ts") or ""
    out = []
    for o in _scored_offers():
        row = dict(o)
        # base_score is always the auto score; a manual override replaces the displayed score
        # (sorting + the +N label) but never the auto value, so overrides are reversible.
        sc = scores.get(o["url"])
        row["base_score"] = o["score"]
        row["score_override"] = bool(sc)
        row["score_reason"] = (sc or {}).get("reason", "")
        row["score_at"] = (sc or {}).get("at")
        if sc:
            row["score"] = sc["score"]
        row["archived"] = bool(o.get("archived_at"))
        # Applied through ANY of the offer's links counts as applied. See _urls_of.
        app_row = next((bot[u] for u in o["urls"] if u in bot), None)
        row["application"] = app_row               # full bot log line, or None
        row["manual_at"] = next((manual[u] for u in o["urls"] if u in manual), None)
        if app_row:
            row["applied_by"] = "bot"
        elif row["manual_at"]:
            row["applied_by"] = "manual"
        else:
            row["applied_by"] = None
        # Queued/dig state joins on ALL of the offer's links, exactly like applied-status: a
        # job posted on both portals is one offer, and it must not queue twice or read as
        # unqueued when the row happens to show the other portal's link. See _urls_of.
        row["queued"] = any(u in queued for u in o["urls"])
        row["dig"] = any(u in dig for u in o["urls"])
        # Outlives the card: a sent card leaves dig_deeper.json, the ✉ on the row stays.
        row["emailed_at"] = max((emailed[u] for u in o["urls"] if u in emailed), default=None)
        out.append(row)
    lh = _last_harvest()
    new_at = lh["at"] if lh else None
    for row in out:
        # "new" = first seen in the most recent Re-harvest run
        row["is_new"] = bool(new_at and row.get("added_at") == new_at)
    return out


@app.get("/api/offers")
def api_offers():
    return {"offers": _enriched_offers(), "harvest": _last_harvest(),
            "generated": datetime.now(timezone.utc).isoformat()}


# Both portals. They are collected before anything is written, so a portal that fails takes
# the whole run down instead of leaving the db half-updated — and, crucially, instead of
# letting one site's silence archive the other site's offers.
SITES = [("justjoin", harvest.fetch_fresh), ("pracuj", harvest_pracuj.fetch_fresh)]


@app.post("/api/harvest")
def api_harvest():
    """Re-collect both feeds and fold them in. Nothing is deleted: offers that fell off a feed
    are stamped `archived_at` on that source, and an offer counts as expired only once every
    portal carrying it has dropped it. Returns the run summary (per-site plus totals)."""
    at = datetime.now(timezone.utc).isoformat()
    harvests = [(site, fetch()) for site, fetch in SITES]
    rows, summary = merge(_read_jsonl(OFFERS_DB), harvests, at)
    write_jsonl(OFFERS_DB, rows)
    log_run(summary)
    return summary


@app.get("/api/harvest")
def api_harvest_status():
    """What the harvest runs did: the last one and the recent history.

    Not the offers — the subpage groups the run's arrivals by company and shows each company's
    other offers alongside them, so it needs the whole db anyway and reads /api/offers for it.
    Every row there already carries `is_new`, so "what came in on the last run" has one
    definition instead of two that can disagree."""
    lh = _last_harvest()
    history = _read_jsonl(HARVEST_LOG)
    return {"last": lh, "history": list(reversed(history))[:20]}


@app.get("/api/history")
def api_history():
    """The application history: every attempt the bot logged (each log line is one event, so a
    retried URL shows every attempt), plus every offer you marked applied by hand. Joined back
    onto the offer db for title/company where the log line lacks them. Newest first.

    An outreach email is not an event of its own: it rides on its offer's application rows as
    `emails`, shown when the row is opened. Only an email whose offer has no application row
    left (you un-ticked "applied by hand" after sending) gets a row, or it would vanish."""
    offers_by_url = _by_any_url()
    events = []
    sent = outreach.sent_log()
    # Spread over each offer's sibling links -- the email may be filed under the pracuj link
    # while the bot applied through the justjoin one.
    emails_of = {}
    for r in sent:
        if r.get("url"):
            for u in _offer_urls(r["url"]):
                emails_of.setdefault(u, []).append(r)
    attached = set()

    def mails(url):
        found = emails_of.get(url, [])
        attached.update(id(r) for r in found)
        return [_email_view(r) for r in found]

    # Bot log — the full trail, one entry per line (not deduped; retries are real history).
    for row in _read_jsonl(LOG):
        o = offers_by_url.get(row.get("url"), {})
        events.append({
            "source": "bot",
            "at": row.get("timestamp"),
            "url": row.get("url"),
            "title": row.get("title") or o.get("title", ""),
            "company": row.get("company") or o.get("company", ""),
            "category": o.get("category", ""),
            "apply_type": row.get("apply_type"),
            "outcome": row.get("outcome"),
            "blocked_reason": row.get("blocked_reason"),
            "cv_used": row.get("cv_used"),
            "composed_answers": row.get("composed_answers") or [],
            "notes": row.get("notes"),
            "diagnostics": row.get("diagnostics"),
            "emails": mails(row.get("url")),
        })

    # Manual marks — just a url + timestamp; join for the human-readable fields.
    for url, at in _manual().items():
        o = offers_by_url.get(url, {})
        events.append({
            "source": "manual",
            "at": at,
            "url": url,
            "title": o.get("title", ""),
            "company": o.get("company", ""),
            "category": o.get("category", ""),
            "apply_type": "manual",
            "outcome": "applied_manual",
            "blocked_reason": None,
            "cv_used": None,
            "composed_answers": [],
            "notes": None,
            "diagnostics": None,
            "emails": mails(url),
        })

    for r in sent:
        if id(r) in attached:
            continue
        o = offers_by_url.get(r.get("url"), {})
        events.append({
            "source": "email",
            "at": r.get("ts"),
            "url": r.get("url"),
            "title": r.get("title") or o.get("title", ""),
            "company": r.get("company") or o.get("company", ""),
            "category": o.get("category", ""),
            "outcome": "emailed",
            "emails": [_email_view(r)],
        })

    events.sort(key=lambda e: e.get("at") or "", reverse=True)
    return {"events": events, "count": len(events),
            "generated": datetime.now(timezone.utc).isoformat()}


def _email_view(r):
    """One outreach_sent.jsonl line, as a history row shows it when opened."""
    return {k: r.get(k) for k in ("ts", "to", "subject", "body", "attachment", "other", "note")}


@app.get("/api/run")
def api_run(url: str, at: str = ""):
    """What one logged application cost to produce: the runner's envelope numbers joined to the
    applier's transcript (`runner/stats.py`). Fetched when a history row is opened, not with the
    list -- a transcript runs to megabytes and most log lines predate run_log.jsonl anyway, so
    paying for all of them up front would buy nothing."""
    return {"run": stats.run_for(url, at)}


class ManualBody(BaseModel):
    url: str


@app.post("/api/manual")
def api_manual(body: ManualBody):
    """Toggle a hand-applied mark for one offer.

    Marks are stored per URL but the toggle is per OFFER: an offer carrying two links can hold
    a mark on either, and unticking has to clear whichever one it is or the row stays applied
    and the click looks broken."""
    manual = _manual()
    urls = _offer_urls(body.url)
    marked = [u for u in urls if u in manual]
    if marked:
        for u in marked:
            del manual[u]
        at = None
    else:
        at = datetime.now(timezone.utc).isoformat()
        manual[body.url] = at
    _save_manual(manual)
    return {"url": body.url, "manual_at": at}


class ScoreBody(BaseModel):
    url: str
    score: int
    reason: str = ""


@app.post("/api/score")
def api_score(body: ScoreBody):
    """Override one offer's score and record why. Empty reason with the score reset to the auto
    value is not special-cased — the override simply persists until you clear manual_scores.json."""
    scores = _manual_scores()
    entry = {"score": body.score, "reason": body.reason.strip(),
             "at": datetime.now(timezone.utc).isoformat()}
    scores[body.url] = entry
    _save_manual_scores(scores)
    return {"url": body.url, **entry}


# ---- the apply queue -----------------------------------------------------------------------
#
# Picking is no longer a one-shot act. A click puts the offer in runner/data/worklist.json
# immediately and it stays there over refreshes, restarts and days, until the nightly runner
# applies to it and deletes it. Everything below therefore reads the file, changes one entry
# and replaces it -- never writes a list it was holding, because run_batch.py is deleting
# from the same file while you click.

class UrlBody(BaseModel):
    url: str


def _queue_view():
    """The queue as the panel shows it: disk order, with score/sites/bucket joined back on
    from the offer db. Those are display fields only -- the file keeps the runner's schema."""
    by_url = _by_any_url()
    items = []
    for e in _queue():
        o = by_url.get(e.get("url"), {})
        items.append(dict(e, score=o.get("score"), sites=o.get("sites", ""),
                          bucket=o.get("bucket"), cities=o.get("cities", [])))
    return items


@app.get("/api/queue")
def api_queue():
    """What is queued, what runs tonight, and what last night's batch did."""
    items = _queue_view()
    return {"items": items, "count": len(items), "cap": NIGHTLY_COUNT,
            "last_batch": _last_batch()}


@app.post("/api/queue/add")
def api_queue_add(body: UrlBody):
    """Queue one offer. A second click on an offer already queued through its OTHER portal
    link is not an add -- the two links are one job and would be applied to twice."""
    o = _by_any_url().get(body.url)
    if not o:
        return {"url": body.url, "queued": False, "reason": "unknown offer"}
    items = _queue()
    urls = set(o["urls"])
    if not any(e.get("url") in urls for e in items):
        items.append(_worklist_entry(o))
        _save_queue(items)
    return {"url": body.url, "queued": True, "count": len(items)}


class OrderBody(BaseModel):
    urls: list[str]


@app.post("/api/queue/reorder")
def api_queue_reorder(body: OrderBody):
    """Queue order IS run order, so a drag is a real decision: it picks what tonight's --limit
    reaches. Applied to the file, not to the order the page was holding -- the runner deletes
    from it while you drag, and an entry it dropped must stay dropped."""
    rest = {e.get("url"): e for e in _queue()}
    items = [rest.pop(u) for u in body.urls if u in rest]
    items.extend(rest.values())          # queued from another tab mid-drag: keep, at the end
    _save_queue(items)
    return {"items": _queue_view(), "count": len(items), "cap": NIGHTLY_COUNT,
            "last_batch": _last_batch()}


@app.post("/api/queue/remove")
def api_queue_remove(body: UrlBody):
    """Unqueue one offer, whichever of its links it was queued under."""
    urls = set(_offer_urls(body.url))
    items = [e for e in _queue() if e.get("url") not in urls]
    _save_queue(items)
    return {"url": body.url, "queued": False, "count": len(items)}


# ---- the dig-deeper list -------------------------------------------------------------------

#
# dig_deeper.json has more writers than the queue: this server, the outreach sender removing
# what it mailed, and any agent you point at the file to fill in contacts or a draft. So every
# write below re-reads the file, changes one card and swaps it in -- and if the file does not
# parse, nothing is written at all: saving over it would throw away the agent's work.

def _broken(e):
    return JSONResponse({"error": str(e)}, status_code=409)


def _dig_key(cards, url):
    """The key a card is filed under -- any of the offer's links, not necessarily this one."""
    return next((u for u in _offer_urls(url) if u in cards), None)


def _card_view(card, ctx):
    return dict(card, **outreach.status(card, ctx))


@app.get("/api/dig")
def api_dig():
    """The outreach cards, each with its stage and send-readiness joined on, furthest along
    first (outreach.order): approved, complete draft, draft missing something, contacts,
    nothing. Within a step, QUEUE order -- the same offers, so you work them in the order the
    bot applies to them -- and cards already drained off the queue keep their file order."""
    try:
        cards = outreach.load()
    except outreach.CardsError as e:
        return {"items": [], "count": 0, "error": str(e)}
    ctx = outreach.Context(siblings=_offer_urls)
    rank = {e.get("url"): i for i, e in enumerate(_queue())}
    items = [_card_view(c, ctx) for c in cards.values()]
    items.sort(key=lambda v: (outreach.order(v), rank.get(v.get("url"), len(rank))))
    return {"items": items, "count": len(items)}


@app.post("/api/dig/add")
def api_dig_add(body: UrlBody):
    """Also chase this one by hand. Additive to the queue, never instead of it: the bot still
    applies through the portal while you go find a human to write to."""
    o = _by_any_url().get(body.url)
    if not o:
        return {"url": body.url, "dig": False, "reason": "unknown offer"}
    try:
        cards = outreach.load()
    except outreach.CardsError as e:
        return _broken(e)
    if not any(u in cards for u in o["urls"]):
        # In front, not appended: the panel shows these in queue order, and file order is
        # the fallback for entries the runner has already drained off the queue -- newest
        # first is the right fallback, they are the ones you were about to write to.
        at = datetime.now(timezone.utc).isoformat()
        cards = {o["url"]: outreach.new_card(o, at), **cards}
        outreach.save(cards)
    return {"url": body.url, "dig": True, "count": len(cards)}


class DigRemoveBody(BaseModel):
    url: str
    force: bool = False


@app.post("/api/dig/remove")
def api_dig_remove(body: DigRemoveBody):
    """Drop a card. One that holds contacts or a draft is refused unless `force` -- the pick
    cycle passes through here, and ten minutes of digging must not vanish on one click."""
    try:
        cards = outreach.load()
    except outreach.CardsError as e:
        return _broken(e)
    keys = [u for u in _offer_urls(body.url) if u in cards]
    worked = [u for u in keys if outreach.has_contacts(cards[u]) or outreach.has_draft(cards[u])]
    if worked and not body.force:
        return {"url": body.url, "dig": True, "needs_force": True,
                "reason": "this card holds contacts or a draft"}
    for u in keys:
        del cards[u]
    if keys:
        outreach.save(cards)
    return {"url": body.url, "dig": False, "count": len(cards)}


class DigUpdateBody(BaseModel):
    url: str
    fields: dict[str, str]


@app.post("/api/dig/update")
def api_dig_update(body: DigUpdateBody):
    """Save the /outreach editor: any of note, email, other, subject, body, cv. Only the fields
    sent are touched, so a field an agent filled meanwhile survives a save of the others. The
    approval stamp is not one of them -- that is /api/dig/approve's alone."""
    try:
        cards = outreach.load()
    except outreach.CardsError as e:
        return _broken(e)
    key = _dig_key(cards, body.url)
    if key is None:
        return JSONResponse({"error": "not on the dig list"}, status_code=404)
    card = cards[key]
    for k, v in body.fields.items():
        if k not in outreach.EDITABLE:
            continue
        v = outreach.text(v)
        card[k] = v.strip() if k in ("email", "subject", "cv") else v.rstrip()
    outreach.save(cards)
    return _card_view(card, outreach.Context(siblings=_offer_urls))


class DigApproveBody(BaseModel):
    url: str
    on: bool


@app.post("/api/dig/approve")
def api_dig_approve(body: DigApproveBody):
    """OK to send: stamp the card with a fingerprint of exactly what would go out now. Any
    later edit to the email, subject, body or CV voids it by itself. `on: false` withdraws."""
    try:
        cards = outreach.load()
    except outreach.CardsError as e:
        return _broken(e)
    key = _dig_key(cards, body.url)
    if key is None:
        return JSONResponse({"error": "not on the dig list"}, status_code=404)
    card, ctx = cards[key], outreach.Context(siblings=_offer_urls)
    if body.on:
        cv = outreach.cv_of(card, ctx)
        probs = outreach.problems(card, cv)
        if not outreach.has_draft(card):
            probs = ["there is no draft to approve"]
        if probs:
            return JSONResponse({"error": "fix first: " + "; ".join(probs)}, status_code=409)
        card["approved"] = outreach.stamp(card, cv)
    else:
        card.pop("approved", None)
    outreach.save(cards)
    return _card_view(card, ctx)


@app.get("/api/cvs")
def api_cvs():
    """Every CV PDF under src/CV_PDF, repo-relative -- the outreach page's CV dropdown."""
    return {"cvs": outreach.cvs()}


# ---- sending ---------------------------------------------------------------------------------
#
# The Send button runs send_outreach.py --send, the same command as by hand, so every rule
# stays in one place: the sender re-judges each card, paces the emails minutes apart and logs
# them. That takes up to ~20 minutes, so it runs as a child process writing SEND_LOG and the
# page polls it. The child shares app.py's console: stopping the server stops the run, which is
# safe -- whatever did not leave yet is simply still approved.

SEND_LOG = HERE / "data" / "outreach_send.log"
_sending = {"proc": None, "started": None}


def _send_state():
    p = _sending["proc"]
    running = bool(p and p.poll() is None)
    log = SEND_LOG.read_text(encoding="utf-8", errors="replace") if SEND_LOG.exists() else ""
    return {"running": running, "started": _sending["started"],
            "exit": None if running or not p else p.returncode,
            "log": log[-8000:], "has_password": bool(send_outreach.password())}


@app.get("/api/outreach/send")
def api_send_state():
    return _send_state()


class SendBody(BaseModel):
    urls: list[str]


@app.post("/api/outreach/send")
def api_send(body: SendBody):
    """Send these cards, in this order -- the ones the page listed in its confirm. A JSON body is
    required on purpose: a cross-site form can't send one, so no other page can press this."""
    if _send_state()["running"]:
        return JSONResponse({"error": "a send is already running"}, status_code=409)
    if not body.urls:
        return JSONResponse({"error": "no cards to send"}, status_code=400)
    if not send_outreach.password():
        return JSONResponse({"error": "GMAIL_APP_PASSWORD is not set"}, status_code=409)
    cmd = [sys.executable, "-u", str(HERE / "send_outreach.py"), "--send"]
    for u in body.urls:
        cmd += ["--url", u]
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    # The sender prints — and → ; a child writing to a file would otherwise use the ANSI codepage.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    with open(SEND_LOG, "w", encoding="utf-8") as log:
        log.write(f"started {started.replace('T', ' ')[:16]} · {len(body.urls)} card(s)\n")
        log.flush()
        _sending["proc"] = subprocess.Popen(cmd, cwd=ROOT, stdout=log,
                                            stderr=subprocess.STDOUT, env=env)
    _sending["started"] = started
    return _send_state()


# The pages share static/offer.js + offer.css, and StaticFiles sends no Cache-Control, so a
# browser is free to keep an old copy of a file the page it just loaded depends on. New HTML
# calling into old JS fails silently -- a row simply loses its pick button. Stamp every /static
# link with the file's mtime, so editing one is the same as pointing the page at a new URL.
def _page(path: Path) -> HTMLResponse:
    def stamp(m: "re.Match[str]") -> str:
        f = HERE / "static" / m.group(1)
        v = int(f.stat().st_mtime) if f.exists() else 0
        return f"/static/{m.group(1)}?v={v}"
    html = re.sub(r"/static/([A-Za-z0-9_.-]+)", stamp, path.read_text(encoding="utf-8"))
    return HTMLResponse(html)


@app.get("/")
def index():
    return _page(PAGE)


@app.get("/harvest")
def harvest_page():
    return _page(HARVEST_PAGE)


@app.get("/history")
def history_page():
    return _page(HISTORY_PAGE)


@app.get("/outreach")
def outreach_page():
    return _page(OUTREACH_PAGE)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)
