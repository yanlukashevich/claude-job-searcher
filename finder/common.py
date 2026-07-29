"""Shared helpers for the finder scripts. Python 3, stdlib only.

Two Windows traps every script here must respect:
- open() defaults to cp1250 on this machine -> always pass encoding='utf-8'.
- justjoin's Cloudflare 403s the default urllib User-Agent -> always send a browser UA.
"""
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

FINDER = Path(__file__).resolve().parent
ROOT = FINDER.parent
DATA = FINDER / "data"
OFFERS_DB = DATA / "offers_db.jsonl"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# Windows console defaults to cp1250 and chokes on city names; never crash on a print.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_json(url):
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def offer_id(title, company):
    """Stable identity: normalized title+company, deliberately without the source site,
    so the same job harvested from justjoin and later pracuj.pl collapses to one record."""
    key = re.sub(r"\s+", " ", (title + "@@" + company).lower().strip())
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


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


def salary_str(employment_types):
    for e in employment_types or []:
        if e.get("currency") == "PLN" and e.get("from"):
            to = int(e.get("to") or e["from"])
            return f"{int(e['from'])}-{to} PLN/{e.get('type', '?')}/{e.get('unit', '?')}"
    return "?"
