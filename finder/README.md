# Finder — how it works and how to run it

Collects every junior+mid offer from justjoin.it and ranks them so the good ones are easy
to find. Two steps, both deterministic Python — no LLM, no browser, no Cowork. Plain
terminal in the project root.

## The pipeline

```
1. harvest.py   CODE  justjoin API -> data/offers_db.jsonl (facts; adds new, archives gone)
2. app.py       CODE  serves the cockpit: joins offers_db + bot log + your manual
                      marks, groups by company, writes src/worklist.json
3. (you) review the cockpit, pick 1-2 per company, hit "Write worklist"
4. Cowork applier reads src/worklist.json, appends to applications_log.jsonl
```

Scoring is a **keyword classifier**, not judgment: code decides facts (is a keyword
present?), the number only **orders** the offers, and a human makes the actual keep/reject
call in the cockpit. See `prototype/README.md` for the buckets and the scoring rules.

## How to run

```powershell
# 1. Harvest (full run: adds new offers, marks vanished ones expired)
python finder\harvest.py
# --days 7 pages only the last week; a partial feed cannot tell "gone" from
# "not in this slice", so it only adds and never archives.

# 2. Start the cockpit, then open http://127.0.0.1:8000
python finder\app.py
```

The **cockpit** (`app.py` + `page.html`) is the one place you look. Offers are grouped by
company; a company with many openings is flagged so you review and pick the best 1–2 instead
of spraying CVs. Click any row to expand what happened — the CV used, the free-text the bot
entered, the outcome, the full notes. Each offer carries a live status: **bot** (from the
append-only log) or **applied by me** (your manual toggle). Tick offers → **Write worklist**
drops them straight into `src/worklist.json` for the Cowork applier. No file downloads.

Every expanded offer also carries a **Copy prompt** button: a ready-to-paste, single-offer
Cowork prompt (read `applier_instructions.md` + `profile.md`, run mode `review`, this offer's
JSON inline). It's the orchestrator's per-subagent task for one offer — paste it into a fresh
Cowork agent to apply to just that offer without going through `worklist.json`.

The **↻ Harvest** link in the header opens a dedicated subpage at **`/harvest`** with one
button that re-pulls the whole live feed. **Nothing is ever deleted:** an offer that fell off
the feed is stamped `archived_at` (**expired**), and one that reappears has the stamp cleared
(`revived_at` records when). The subpage shows tiles (`+new`, expired, revived, in db, live,
archived-total), a table of recent runs, and the list of offers that came in on the last run.
Back in the cockpit, freshly-harvested offers get a **new** stats tile and a `NEW` badge. This
replaces running `harvest.py` by hand, though the CLI still works. Because archiving stamps
rows that are already stored, `offers_db.jsonl` is written atomically (temp file + swap) — it
is no longer append-only. Each run also appends to `data/harvest_log.jsonl` (the run history).

**Expired offers in the cockpit** are hidden by default. The `hide expired / + expired / only
expired` selector in the header switches them in; shown ones are dimmed, dashed and carry an
`EXPIRED` badge, and the `expired` stat tile always reports how many the db is holding. The
selector also drives the category counts (chips and dropdown), so the numbers always describe
the offers you can actually see.

Three files, three owners, joined by offer URL:

| file | who writes it | how |
|---|---|---|
| `data/offers_db.jsonl` | `harvest.py` / Re-harvest | atomic rewrite (temp + swap): adds new rows, stamps `archived_at` on vanished ones |
| `../src/applications_log.jsonl` | the Cowork applier | append-only (crash-safe) |
| `data/manual_applied.json` | you, via the cockpit | mutable dict, toggle on/off |

**Superseded:** `prototype/browse.py` (static triage page, applied-state in localStorage) and
the whole `legacy/` PowerShell pipeline (`harvest_offers.ps1` + `build_worklist.ps1` +
`offers_queue.json`). The cockpit does harvest, triage and worklist-writing, backed by the real
log instead of the browser. The legacy files are frozen for reference (`legacy/README.md`).

Tuning loop for scoring: edit `prototype\keywords.py` → restart `app.py` → refresh the tab.

## The files

| file | what it is |
|---|---|
| `harvest.py` | Fetches the offers into `data/offers_db.jsonl`. |
| `common.py` | Shared stdlib helpers (Chrome UA, UTF-8, stable offer id). |
| `data/offers_db.jsonl` | Every offer ever seen; one line per unique job. Rows are never deleted — gone-from-the-feed ones carry `archived_at`. |
| `prototype/` | **The scorer + review page.** `keywords.py` is the file you tune. |

## Identity & dedup

- An offer's `id` = hash of normalized **title+company** — deliberately without the source
  site, so the same job harvested from justjoin and later pracuj.pl collapses into one
  record. Per-city clones on justjoin collapse the same way (cities are unioned).
- Anti-double-apply now lives in the cockpit, not in a script: every offer carries a live
  **applied** status joined from `src/applications_log.jsonl` (bot) and `manual_applied.json`
  (you), so you skip the ones already done when you pick. It is a human-in-the-loop check, not
  the old automatic set-filter — the deprecated `legacy/build_worklist.ps1` did that.

## Gotchas (learned the hard way — do not rediscover)

- The API 403s non-browser User-Agents (Cloudflare). All scripts send a Chrome UA.
- `itemsCount` paginates, `cursor` lies, `itemsPerPage` is ignored
  (see `..\docs\JUSTJOIN_API_NOTES.md`).
- Everything is UTF-8 explicitly — Windows Python defaults to cp1250 and mangles
  Polish city names silently.
- `experienceLevel` and `category` are set by employers and lie routinely; the scorer leans
  on title/skill keywords, not the labels.
