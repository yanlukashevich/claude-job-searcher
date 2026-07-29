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
  python finder/app.py            # http://127.0.0.1:8000
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

from common import ROOT, write_jsonl              # noqa: E402
from scoring import classify, BUCKETS            # noqa: E402
from harvest import fetch_fresh, merge            # noqa: E402

OFFERS_DB = HERE / "data" / "offers_db.jsonl"
MANUAL = HERE / "data" / "manual_applied.json"
MANUAL_SCORES = HERE / "data" / "manual_scores.json"   # url -> {score, reason, at} (your overrides)
LAST_HARVEST = HERE / "data" / "last_harvest.json"
HARVEST_LOG = HERE / "data" / "harvest_log.jsonl"   # one line per Re-harvest run (append-only)
LOG = ROOT / "src" / "applications_log.jsonl"
WORKLIST = ROOT / "src" / "worklist.json"
PAGE = HERE / "page.html"
HARVEST_PAGE = HERE / "harvest.html"
HISTORY_PAGE = HERE / "history.html"

# offer category (finder taxonomy) -> CV variant stack (profile.md CV-variants table).
# Anything not listed falls through to "universal", which is also the applier's default.
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
    for s in offer.get("sources", []):
        if s.get("url"):
            return s["url"]
    return ""


# Scoring 3500 offers is regex-heavy, but the db only changes when harvest.py runs. Cache the
# scored rows and rebuild only when the file's mtime moves. The log and manual marks are tiny
# and change often (every bot run, every click), so those are re-read on every request.
_cache = {"mtime": None, "offers": None}


def _scored_offers():
    mtime = OFFERS_DB.stat().st_mtime if OFFERS_DB.exists() else 0
    if _cache["mtime"] == mtime:
        return _cache["offers"]
    offers = []
    for o in _read_jsonl(OFFERS_DB):
        bucket, score, why = classify(o)
        cat = o.get("category", "?")
        offers.append({
            "url": _url_of(o),
            "title": o.get("title", ""),
            "company": o.get("company", ""),
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
        app_row = bot.get(o["url"])
        row["application"] = app_row               # full bot log line, or None
        row["manual_at"] = manual.get(o["url"])    # iso string, or None
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


@app.post("/api/harvest")
def api_harvest():
    """Re-collect the whole justjoin feed and fold it in. Nothing is deleted: offers that fell
    off the feed are stamped `archived_at` (expired) and offers that came back are un-stamped.
    Returns the run summary and stamps last_harvest.json."""
    at = datetime.now(timezone.utc).isoformat()
    fresh = fetch_fresh(0)                                  # {id: offer} — full re-collect
    merged, summary = merge(_read_jsonl(OFFERS_DB), fresh, at)
    write_jsonl(OFFERS_DB, merged)
    LAST_HARVEST.parent.mkdir(parents=True, exist_ok=True)
    LAST_HARVEST.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with HARVEST_LOG.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")
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
                                   "score": o["score"], "bucket_name": o["bucket_name"]})
        new_offers.sort(key=lambda x: -x["score"])
    return {"last": lh, "history": list(reversed(history))[:20], "new_offers": new_offers}


@app.get("/api/history")
def api_history():
    """The application history: every attempt the bot logged (each log line is one event, so a
    retried URL shows every attempt), plus every offer you marked applied by hand. Joined back
    onto the offer db for title/company where the log line lacks them. Newest first."""
    offers_by_url = {o["url"]: o for o in _scored_offers()}
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
    """Toggle a hand-applied mark for one offer URL."""
    manual = _manual()
    if body.url in manual:
        del manual[body.url]
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
    by_url = {o["url"]: o for o in _scored_offers()}
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
    uvicorn.run(app, host="127.0.0.1", port=8000)
