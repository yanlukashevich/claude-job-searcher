"""Shared helpers for the finder scripts. Python 3, stdlib only.

Two Windows traps every script here must respect:
- open() defaults to cp1250 on this machine -> always pass encoding='utf-8'.
- justjoin's Cloudflare 403s the default urllib User-Agent -> always send a browser UA.
"""
import gzip
import hashlib
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

FINDER = Path(__file__).resolve().parent
ROOT = FINDER.parent
DATA = FINDER / "data"
OFFERS_DB = DATA / "offers_db.jsonl"
LAST_HARVEST = DATA / "last_harvest.json"          # the most recent run's summary
HARVEST_LOG = DATA / "harvest_log.jsonl"           # one line per run (append-only)
COMPANY_ALIASES = DATA / "company_aliases.json"    # company name -> canonical key (hand-written)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# Windows console defaults to cp1250 and chokes on city names; never crash on a print.
# Under pythonw.exe (the scheduled worklist run) there is no console at all and stdout is None --
# print() tolerates that, this line would not.
if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_json(url):
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def get_html(url):
    """A page, not an API. pracuj serves ~3 MB of HTML per listing page, so ask for gzip."""
    req = urllib.request.Request(url, headers={
        "accept": "text/html", "accept-encoding": "gzip",
        "accept-language": "pl-PL,pl;q=0.9,en;q=0.8", "user-agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if r.headers.get("content-encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8")


# ---- identity ------------------------------------------------------------------------------
#
# Identity is derived from the display strings, so anything the two portals spell differently
# forks one job into two records. They differ constantly: "LUX MED Sp. z o.o." vs
# "LUX MED Sp. z o. o.", "Comarch SA" vs "COMARCH", "(k/m)" vs "(m/k)". Every one of those cost
# a cross-portal link until the strings below started being reduced to a key before hashing.
# The raw strings stay on the row untouched -- this is the identity layer, not the display one.

_INVISIBLE = dict.fromkeys(map(ord, "​‌‍‎‏﻿"), None)

# Legal forms, in the many spellings a person typing a company name produces. Stripped because
# one portal's listing carries them and the other's does not; they never distinguish two
# employers you could actually apply to separately.
_LEGAL = re.compile(r"\b(?:sp(?:olka)?\s*z\s*o+\s*o+|z\s*o+\s*o+|spzoo|s\s*a|sp\s*k|sp\s*j"
                    r"|s\s*c|llc|ltd|inc|gmbh|polska|poland)\b")

# "(k/m)", "(m/f/d)", "| f/m/d" -- a gender marker, not part of the job. Single letters only,
# so "UX/UI" and "CI/CD" are untouched.
_GENDER = re.compile(r"[kmfwdx](?:\s*/\s*[kmfwdx])+")


def clean_text(s):
    """Ingest hygiene for a display string: NFKC (turns NBSP into a real space), drop
    zero-width characters, collapse runs of whitespace.

    Invisible characters are the worst kind of duplicate -- two titles that look identical on
    screen hash differently and nothing about the cockpit explains why."""
    s = unicodedata.normalize("NFKC", s or "").translate(_INVISIBLE)
    return " ".join(s.split())


# Letters NFKD will not take apart, because the mark is not a combining accent but part of the
# glyph. Without this 'Obsługa' keys as 'obs uga' -- the word is cut in half, not de-accented.
_LETTERS = str.maketrans({"ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ø": "o", "Ø": "O",
                          "ß": "ss", "æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE"})


def _defold(s):
    """Drop diacritics: 'Obsługa' and 'Obsluga' are one word for keying purposes."""
    s = unicodedata.normalize("NFKD", (s or "").translate(_LETTERS))
    return "".join(c for c in s if not unicodedata.combining(c))


_alias_cache = None


def _aliases():
    """Hand-written {any spelling: the name to use instead}, e.g. {"COMARCH": "Comarch"}.

    It does two jobs with one entry, because they are the same job. The value's key replaces
    the entry's key, so pointing two spellings at one name merges them -- which is the only way
    to state what the mechanical normalizer cannot infer (a rebrand, "Grupa X" vs "X"). And the
    value is written the way you want it read, so it is also what the cockpit displays.

    An entry whose value keys the same as its key is therefore display-only and safe. One that
    keys differently changes ids: rerun migrate_offer_ids.py after adding it.

    Read once per process: norm_company runs a few times per offer over thousands of offers."""
    global _alias_cache
    if _alias_cache is None:
        raw = (json.loads(COMPANY_ALIASES.read_text(encoding="utf-8"))
               if COMPANY_ALIASES.exists() else {})
        _alias_cache = {_company_key(k): v.strip() for k, v in raw.items() if v.strip()}
    return _alias_cache


def _company_key(name):
    key = _defold(clean_text(name)).lower().replace("&", " and ")
    key = re.sub(r"[^a-z0-9]+", " ", key).strip()
    prev = None
    while prev != key:                       # "Sp. z o.o. Sp. k." needs more than one pass
        prev = key
        key = " ".join(_LEGAL.sub(" ", key).split())
    # A name that is *only* a legal form would key to "" and pull every such company together.
    return key or re.sub(r"[^a-z0-9]+", " ", _defold(name or "").lower()).strip()


def norm_company(name):
    """The company's identity key. 'LUX MED Sp. z o. o.' -> 'lux med'."""
    key = _company_key(name)
    alias = _aliases().get(key)
    return _company_key(alias) if alias else key


def norm_title(title):
    """The job's identity key. '+' and '#' survive, so C++ and C# stay distinct."""
    t = _GENDER.sub(" ", _defold(clean_text(title)).lower())
    return " ".join(re.sub(r"[^a-z0-9+#]+", " ", t).split())


def offer_id(title, company):
    """Stable identity: normalized title+company, deliberately without the source site, so a
    job harvested from both justjoin and pracuj.pl collapses to one record carrying both."""
    key = norm_title(title) + "@@" + norm_company(company)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def canonical_names(rows):
    """{company key: the spelling to display}. Several rows of one employer carry several
    spellings; the cockpit has to pick one or the same company heads two groups. Most common
    wins, ties go to the longest -- 'Netia' beats 'NETIA', 'Comarch SA' beats 'Comarch' only
    if it is at least as common. company_aliases.json overrides the vote."""
    seen = {}
    for r in rows:
        name = r.get("company", "")
        if name:
            spellings = seen.setdefault(norm_company(name), {})
            spellings[name] = spellings.get(name, 0) + 1
    names = {k: max(v, key=lambda n: (v[n], len(n))) for k, v in seen.items()}
    names.update({_company_key(alias): alias for alias in _aliases().values()})
    return names


def read_jsonl(path):
    if not path.exists():
        return []
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            # A line that will not parse is a record the pipeline cannot see. Fail loudly.
            sys.exit(f"FATAL: {path.name} line {n} is not valid JSON. Repair it before running.")
    return out


def append_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_jsonl(path, records):
    """Rewrite a jsonl file atomically (tmp + replace). Archiving stamps a field on rows that
    are already stored, so the file cannot be append-only any more; the swap keeps a crash from
    leaving a half-written db behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)


def union_sources(stored, incoming):
    """Add sources to a row, keyed by URL. Used while collapsing one harvest.

    Keyed by URL rather than by site because one portal does publish the same job twice --
    two postings, two slugs, two apply links, one identity once the titles normalize. Keeping
    only the first would hide a link you may already have applied through."""
    srcs = stored.setdefault("sources", [])
    have = {s.get("url") for s in srcs}
    for src in incoming:
        if src.get("url") not in have:
            srcs.append(dict(src))
            have.add(src.get("url"))


def sync_sources(stored, incoming, at):
    """Fold one site's harvest into a stored offer; that site's rows are the truth about it.
    Returns True if the site is new to this offer (i.e. the portals just got linked).

    The same job posted on both portals collapses to one id (see offer_id), so the second
    site must be *added* to sources rather than dropped on the floor -- otherwise the offer
    keeps only whichever portal happened to find it first, and its other link is lost.

    A URL this site no longer carries is archived even though the offer itself is still live:
    a re-posted job comes back under a new slug, and without this the row would keep pointing
    at the dead one. The old entry stays on the row -- it is how an application filed through
    that link is still recognised as an application to this job.
    """
    site = incoming[0]["site"] if incoming else None
    srcs = stored.setdefault("sources", [])
    known = {s.get("url"): s for s in srcs if s.get("site") == site}
    fresh_urls = set()
    for src in incoming:
        fresh_urls.add(src.get("url"))
        cur = known.get(src.get("url"))
        if cur is None:
            srcs.append(dict(src))
        else:
            cur.pop("archived_at", None)        # this site's feed still carries this link
            cur.update({k: v for k, v in src.items() if k != "archived_at"})
    for url, s in known.items():
        if url not in fresh_urls and not s.get("archived_at"):
            s["archived_at"] = at
    return bool(incoming) and not known


def merge(existing, harvests, at, archive_missing=True):
    """Fold one run's harvests into the stored rows. Returns (rows, summary).

    `harvests` is [(site, {id: offer}), ...] -- every site collected in this run. They are
    merged together rather than one call per site because expiry is decided over ALL of them:
    a justjoin-only merge would see pracuj's offers missing from its feed and, speaking only
    for justjoin, still have to leave them alone.

    Nothing is ever deleted. Archiving is per SOURCE: a site's full harvest can testify about
    that site alone, so it stamps `archived_at` on its own source entry. The offer itself
    counts as expired once *every* source is archived, and revives the moment any portal
    carries it again. Only a FULL harvest can tell "gone" from "not in this slice", so a
    --days run passes archive_missing=False and merely adds.
    """
    by_id = {o["id"]: o for o in existing}
    for o in by_id.values():
        # Rows archived before expiry became per-source carry the stamp only at the top. Push
        # it down, or the first harvest of a site they were never on would read "no source is
        # archived" and revive every one of them.
        srcs = o.get("sources") or []
        if o.get("archived_at") and not any(s.get("archived_at") for s in srcs):
            for s in srcs:
                s["archived_at"] = o["archived_at"]
    per_site = []
    for site, fresh in harvests:
        added = linked = 0
        for oid, o in fresh.items():
            cur = by_id.get(oid)
            if cur is None:
                o["added_at"] = at
                by_id[oid] = o
                added += 1
            elif sync_sources(cur, o["sources"], at):
                linked += 1                    # already known from the other portal
        if archive_missing:
            for oid, o in by_id.items():
                if oid in fresh:
                    continue
                for s in o.get("sources", []):
                    if s.get("site") == site and not s.get("archived_at"):
                        s["archived_at"] = at
        per_site.append({"site": site, "added": added, "linked": linked, "live": len(fresh)})
    archived = revived = 0
    for o in by_id.values():
        srcs = o.get("sources") or []
        gone = bool(srcs) and all(s.get("archived_at") for s in srcs)
        if gone and not o.get("archived_at"):
            o["archived_at"] = at
            archived += 1
        elif not gone and o.pop("archived_at", None):
            o["revived_at"] = at
            revived += 1
    rows = list(by_id.values())
    return rows, {"at": at, "sites": per_site,
                  "added": sum(s["added"] for s in per_site),
                  "linked": sum(s["linked"] for s in per_site),
                  "live": sum(s["live"] for s in per_site),
                  "archived": archived, "revived": revived, "total": len(rows),
                  "archived_total": sum(1 for o in rows if o.get("archived_at")),
                  # a partial run saw one slice of one feed: its live/archived columns do not
                  # describe the market, so the harvest page labels the row instead of
                  # letting it read like a full sweep that suddenly found 700 offers.
                  "partial": not archive_missing or len(harvests) < 2}


def log_run(summary):
    """Record a finished harvest. Every path that merges calls this, not just the cockpit
    button -- a run that writes the db but leaves no trace makes the harvest page read as if
    the offers now in the cockpit never arrived."""
    DATA.mkdir(parents=True, exist_ok=True)
    LAST_HARVEST.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    append_jsonl(HARVEST_LOG, [summary])


def salary_str(employment_types):
    for e in employment_types or []:
        if e.get("currency") == "PLN" and e.get("from"):
            to = int(e.get("to") or e["from"])
            return f"{int(e['from'])}-{to} PLN/{e.get('type', '?')}/{e.get('unit', '?')}"
    return "?"
