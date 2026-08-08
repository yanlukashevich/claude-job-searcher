"""One page, one source of truth. The apply cockpit.

Serves offers.html and a tiny JSON API that JOINS three files by offer URL:
  - finder/data/offers_db.jsonl   the offers (harvest.py writes it; rows are never deleted,
                                  vanished ones are stamped archived_at)
  - src/applications_log.jsonl    what the BOT did (applier appends; append-only)
  - finder/data/manual_applied.json   what YOU did by hand (mutable, toggle-able)

The two write patterns are different on purpose. Automated runs append to the JSONL log
(crash-safe, no read-modify-write). Your manual marks are one interactive click, so they live
in a plain mutable dict you can toggle on and off -- you cannot un-append a JSONL line.

Run:
  python finder/app.py            # http://127.0.0.1:9000
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent           # finder/
sys.path.insert(0, str(HERE))                    # common
sys.path.insert(0, str(HERE / "prototype"))      # scoring, keywords

from common import (ROOT, HARVEST_LOG, LAST_HARVEST,   # noqa: E402
                    canonical_names, log_run, merge, norm_company, write_jsonl)
from scoring import classify, BUCKETS            # noqa: E402
import harvest                                    # noqa: E402  justjoin
import harvest_pracuj                             # noqa: E402  pracuj.pl

OFFERS_DB = HERE / "data" / "offers_db.jsonl"
MANUAL = HERE / "data" / "manual_applied.json"
MANUAL_SCORES = HERE / "data" / "manual_scores.json"   # url -> {score, reason, at} (your overrides)
LOG = ROOT / "src" / "applications_log.jsonl"
WORKLIST = ROOT / "src" / "worklist.json"
PAGE = HERE / "page.html"
HARVEST_PAGE = HERE / "harvest.html"
HISTORY_PAGE = HERE / "history.html"

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


def _last_harvest():
    if LAST_HARVEST.exists():
        return json.loads(LAST_HARVEST.read_text(encoding="utf-8"))
    return None


# ---- API -----------------------------------------------------------------------------------

@app.get("/api/offers")
def api_offers():
    bot = _bot_applications()
    manual = _manual()
    scores = _manual_scores()
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
        out.append(row)
    lh = _last_harvest()
    new_at = lh["at"] if lh else None
    for row in out:
        # "new" = first seen in the most recent Re-harvest run
        row["is_new"] = bool(new_at and row.get("added_at") == new_at)
    return {"offers": out, "harvest": lh,
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
    """State for the harvest subpage: the last run, the recent run history, and the offers
    that came in on the most recent run (so you can see exactly what's new)."""
    lh = _last_harvest()
    history = _read_jsonl(HARVEST_LOG)
    new_at = lh["at"] if lh else None
    new_offers = []
    if new_at:
        for o in _scored_offers():
            if o.get("added_at") == new_at:
                new_offers.append({"title": o["title"], "company": o["company"],
                                   "url": o["url"], "category": o["category"],
                                   "sites": o["sites"],
                                   "score": o["score"], "bucket_name": o["bucket_name"]})
        new_offers.sort(key=lambda x: -x["score"])
    return {"last": lh, "history": list(reversed(history))[:20], "new_offers": new_offers}


@app.get("/api/history")
def api_history():
    """The application history: every attempt the bot logged (each log line is one event, so a
    retried URL shows every attempt), plus every offer you marked applied by hand. Joined back
    onto the offer db for title/company where the log line lacks them. Newest first."""
    offers_by_url = _by_any_url()
    events = []

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
        })

    events.sort(key=lambda e: e.get("at") or "", reverse=True)
    return {"events": events, "count": len(events),
            "generated": datetime.now(timezone.utc).isoformat()}


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


class WorklistBody(BaseModel):
    urls: list[str]


@app.post("/api/worklist")
def api_worklist(body: WorklistBody):
    """Write the picked offers to src/worklist.json in the shape the applier consumes."""
    by_url = _by_any_url()
    items = []
    for u in body.urls:
        o = by_url.get(u)
        if not o:
            continue
        items.append({
            "url": o["url"],
            "title": o["title"],
            "company": o["company"],
            "location": ", ".join(o["cities"]),
            "stack": o["stack"],
            "apply_method": o.get("apply_method", ""),
            "apply_url": o.get("apply_url", ""),
            "status": "pending",
        })
    WORKLIST.parent.mkdir(parents=True, exist_ok=True)
    WORKLIST.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"written": len(items), "path": str(WORKLIST)}


@app.get("/")
def index():
    return FileResponse(PAGE)


@app.get("/harvest")
def harvest_page():
    return FileResponse(HARVEST_PAGE)


@app.get("/history")
def history_page():
    return FileResponse(HISTORY_PAGE)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)
