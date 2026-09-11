"""The outreach card: what a dig-deeper entry is, and when it may be emailed. A library, no CLI.

finder/data/dig_deeper.json holds one card per offer you want to chase by hand. It fills up in
stages -- no contact -> contacts -> draft -> approved -> sent -- and every stage is just fields
on the card, which the cockpit's /outreach page and any agent you point at the file edit
directly. app.py and send_outreach.py both judge cards through this module, so the page and the
sender can never disagree about whether a card is ready.

Approval is a stamp, not a flag: the OK-to-send button stores a short hash of exactly what will
go out (email + subject + body + CV). An edit to any of those after approving -- in the page or
straight in the file -- stops the stamp matching, so the card drops back to draft by itself.
Nothing has to watch for edits; the sender re-checks the stamp right before each send.
"""
import hashlib
import json
import re

from common import DATA, OFFERS_DB, ROOT, write_json

DIG = DATA / "dig_deeper.json"
SENT_LOG = DATA / "outreach_sent.jsonl"         # one line per email that left, with its text
MANUAL = DATA / "manual_applied.json"
APP_LOG = ROOT / "runner" / "data" / "applications_log.jsonl"
CV_DIR = ROOT / "src" / "CV_PDF"

# The card's key order on disk. The file is read and edited by hand and by agents, so it is
# written in one stable shape: offer facts first, then the fields a human or agent fills in.
# `approved` is last and written only when set -- it belongs to the OK-to-send button alone.
FACTS = ["url", "company", "title", "apply_url", "cities", "score", "added_at"]
EDITABLE = ["note", "email", "other", "subject", "body", "cv"]
ORDER = FACTS + EDITABLE + ["approved"]

STAGES = ["no contact", "contacts", "draft", "approved"]

# Outcomes that mean an application actually went out. The drafts say "I already applied",
# so anything else -- a block, no attempt at all -- holds the email back. A review-mode fill
# counts as sent: in the owner's practice those applications do go out.
SENT_OUTCOMES = {"applied_clean", "applied_composed", "applied_manual", "submitted",
                 "filled_review"}

EMAIL = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[A-Za-z]{2,}$")
CV_PATH = re.compile(r"(?:src/)?CV_PDF/\S+?\.pdf", re.I)


class CardsError(Exception):
    """dig_deeper.json does not parse. Raised instead of returning {} so no caller ever
    'saves' an empty list over a file an agent merely left broken."""


# ---- the file ------------------------------------------------------------------------------

def load():
    """url -> card, as it is on disk right now."""
    if not DIG.exists():
        return {}
    txt = DIG.read_text(encoding="utf-8")
    if not txt.strip():
        return {}
    try:
        cards = json.loads(txt)
    except json.JSONDecodeError as e:
        raise CardsError(f"{DIG.name} is not valid JSON: line {e.lineno}, column {e.colno}: "
                         f"{e.msg}. Fix the file; nothing is written until it parses.") from None
    if not isinstance(cards, dict) or not all(isinstance(c, dict) for c in cards.values()):
        raise CardsError(f"{DIG.name} must be an object of url -> card objects.")
    for url, c in cards.items():
        c.setdefault("url", url)
    return cards


def _shaped(card):
    out = {k: card.get(k, "") for k in ORDER if k in card or k in EDITABLE}
    if not out.get("approved"):
        out.pop("approved", None)
    out.update({k: v for k, v in card.items() if k not in out and k != "approved"})
    return out


def save(cards):
    write_json(DIG, {u: _shaped(c) for u, c in cards.items()})


def new_card(offer, at):
    """The card /api/dig/add files: the offer's facts plus every fillable field, empty -- so
    whoever opens the file next sees the slots, not a schema to remember."""
    return _shaped({"url": offer["url"], "company": offer["company"], "title": offer["title"],
                    "apply_url": offer.get("apply_url", ""), "cities": offer.get("cities", []),
                    "score": offer.get("score"), "added_at": at})


def remove(urls):
    """Drop the card filed under any of `urls`. Re-reads first: the sender calls this minutes
    after it loaded the file, and a click or an agent edit made meanwhile must survive."""
    cards = load()
    gone = [u for u in urls if u in cards]
    for u in gone:
        del cards[u]
    if gone:
        save(cards)
    return gone


def text(s):
    """A field as it is compared and sent: \\r\\n from a pasted or hand-edited value is the same
    text as \\n, and must not read as an edit that voids the approval."""
    return (s or "").replace("\r\n", "\n")


# ---- the rest of the world a card is judged against ----------------------------------------

def _jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def sent_log():
    return _jsonl(SENT_LOG)


def _db_siblings():
    """url -> every link its offer has ever had. The light version of app.py's _offer_urls,
    for the sender, which has no business scoring 3500 offers to answer this."""
    idx = {}
    for row in _jsonl(OFFERS_DB):
        urls = [s["url"] for s in row.get("sources", []) if s.get("url")]
        for u in urls:
            idx.setdefault(u, urls)
    return lambda url: idx.get(url) or [url]


def resolve_cv(value):
    """A CV reference -> the repo-relative path of a PDF that exists, or ''. The bot logs
    `CV_PDF/...` relative to src/, sometimes with a remark after it; the card stores
    `src/CV_PDF/...` relative to the repo root. Both resolve here."""
    m = CV_PATH.search((value or "").replace("\\", "/"))
    if not m:
        return ""
    path = m.group(0)
    if not path.lower().startswith("src/"):
        path = "src/" + path
    return path if (ROOT / path).is_file() else ""


class Context:
    """Everything a card's status depends on besides the card, read once per request or run:
    the bot log, your manual applied-marks, the sent log, and which links are one offer."""

    def __init__(self, siblings=None):
        self.siblings = siblings or _db_siblings()
        self.bot = {}
        for row in _jsonl(APP_LOG):
            if row.get("url"):
                self.bot.setdefault(row["url"], []).append(row)
        self.manual = json.loads(MANUAL.read_text(encoding="utf-8")) if MANUAL.exists() else {}
        self.sent = sent_log()

    def urls(self, card):
        return self.siblings(card.get("url", ""))

    def application(self, card):
        """{sent, outcome, at, manual_at}: did an application go out, through any link?"""
        urls = self.urls(card)
        rows = sorted((r for u in urls for r in self.bot.get(u, [])),
                      key=lambda r: r.get("timestamp") or "", reverse=True)
        manual = next((self.manual[u] for u in urls if u in self.manual), None)
        best = next((r for r in rows if r.get("outcome") in SENT_OUTCOMES), None) \
            or (rows[0] if rows else None)
        return {"sent": bool(manual or (best and best.get("outcome") in SENT_OUTCOMES)),
                "outcome": best.get("outcome") if best else None,
                "at": best.get("timestamp") if best else None,
                "manual_at": manual}

    def cv_used(self, card):
        """The CV the bot sent with this offer's application, if it names a file that exists:
        the default attachment, so the email and the application match."""
        urls = self.urls(card)
        rows = sorted((r for u in urls for r in self.bot.get(u, [])),
                      key=lambda r: r.get("timestamp") or "", reverse=True)
        return next((p for p in (resolve_cv(r.get("cv_used")) for r in rows) if p), "")

    def sent_to(self, card):
        """The sent-log line for this offer + this address, if one exists. The pair, not the
        offer: a second contact at the same company is a new email, the same one is not."""
        urls = set(self.urls(card))
        to = (card.get("email") or "").strip().lower()
        return next((r for r in self.sent
                     if r.get("url") in urls and (r.get("to") or "").lower() == to), None)

    def emailed(self, urls):
        """The newest sent-log timestamp for any of `urls`, or None."""
        urls = set(urls)
        ts = [r.get("ts") or "" for r in self.sent if r.get("url") in urls]
        return max(ts) if ts else None


# ---- the rules -----------------------------------------------------------------------------

def cv_of(card, ctx):
    return (card.get("cv") or "").strip().replace("\\", "/") or ctx.cv_used(card)


def stamp(card, cv):
    """A short fingerprint of exactly what goes out. `cv` is the CV after the fallback."""
    parts = [(card.get("email") or "").strip(), text(card.get("subject")).strip(),
             text(card.get("body")), cv]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:12]


def is_approved(card, cv):
    return bool(card.get("approved")) and card["approved"] == stamp(card, cv)


def has_contacts(card):
    return bool((card.get("email") or "").strip() or (card.get("other") or "").strip())


def has_draft(card):
    return bool(text(card.get("subject")).strip() or text(card.get("body")).strip())


def stage(card, cv):
    if has_draft(card):
        return "approved" if is_approved(card, cv) else "draft"
    return "contacts" if has_contacts(card) else "no contact"


def problems(card, cv):
    """What stops this card from being sendable, in words. A card with no draft yet has only
    one possible problem -- a malformed email -- everything else is simply not started."""
    out = []
    email = (card.get("email") or "").strip()
    if email and not EMAIL.match(email):
        out.append(f"'{email}' is not one valid email address (a second one goes in other)")
    if not has_draft(card):
        return out
    if not email:
        out.append("no email to send to")
    if not text(card.get("subject")).strip():
        out.append("the subject is empty")
    if not text(card.get("body")).strip():
        out.append("the body is empty")
    if not cv:
        out.append("no CV: pick one (the bot's CV for this offer is unknown)")
    elif not (ROOT / cv).is_file():
        out.append(f"CV not found: {cv}")
    return out


def held_reason(card, ctx):
    """Why a finished, approved draft still may not go: the email says you already applied."""
    app = ctx.application(card)
    if app["sent"]:
        return None
    if app["outcome"]:
        return f"the application isn't submitted yet (bot: {app['outcome']})"
    return "the application isn't submitted yet (no application logged)"


def status(card, ctx):
    """Everything the page and the sender show about one card, beyond its own fields."""
    cv = cv_of(card, ctx)
    sent = ctx.sent_to(card) if (card.get("email") or "").strip() else None
    st = {
        "stage": stage(card, cv),
        "has_contacts": has_contacts(card),
        "approved_ok": is_approved(card, cv),
        "approval_stale": bool(card.get("approved")) and not is_approved(card, cv),
        "problems": problems(card, cv),
        "held": held_reason(card, ctx),
        "cv_used": ctx.cv_used(card),
        "cv_effective": cv,
        "application": ctx.application(card),
        "sent_at": sent.get("ts") if sent else None,
    }
    # What the send button counts and the sender sends: one definition for both.
    st["ready"] = (has_draft(card) and st["approved_ok"] and not st["problems"]
                   and not st["held"] and not st["sent_at"])
    return st


def order(view):
    """Sort key of a card with its status joined on: furthest along first -- approved, then a
    complete draft, then one still missing something, then contacts, then nothing. Within a
    stage, what can go now before what is held."""
    return (-STAGES.index(view["stage"]), not view["ready"], bool(view["problems"]),
            bool(view["held"]))


def cvs():
    """Every CV on disk, repo-relative -- the page's CV dropdown."""
    if not CV_DIR.exists():
        return []
    return sorted(p.relative_to(ROOT).as_posix() for p in CV_DIR.rglob("*.pdf"))
