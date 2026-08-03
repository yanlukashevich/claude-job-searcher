# Finder — how it works and how to run it

Collects every junior+mid offer from **justjoin.it** and **pracuj.pl** and ranks them so the
good ones are easy to find. Two steps, both deterministic Python — no LLM, no browser, no
Cowork. Plain terminal in the project root.

## The pipeline

```
1. harvest.py          CODE  justjoin API   -> data/offers_db.jsonl (facts; adds new, archives gone)
   harvest_pracuj.py   CODE  pracuj listing -> the same file, same row shape
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
python finder\harvest.py            # justjoin.it  (~40 s)
python finder\harvest_pracuj.py     # pracuj.pl    (~2 min, 42 pages)
# --days 7 pages only the last week; a partial feed cannot tell "gone" from
# "not in this slice", so it only adds and never archives. justjoin only.

# 2. Start the cockpit, then open http://127.0.0.1:8000
python finder\app.py
```

The **↻ Harvest** button in the cockpit runs *both* portals in one go, which is the normal
way to do it — the CLI scripts exist so a single portal can be re-pulled or debugged alone.

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
button that re-pulls **both live feeds**. **Nothing is ever deleted:** an offer that fell off a
feed is stamped `archived_at` on *that portal's* source entry, and only counts as expired once
every portal carrying it has dropped it; one that reappears has the stamp cleared
(`revived_at` records when). The subpage shows tiles (`+new`, expired, revived, in db, live,
archived-total), a table of recent runs, and the list of offers that came in on the last run.
Back in the cockpit, freshly-harvested offers get a **new** stats tile and a `NEW` badge. This
replaces running `harvest.py` by hand, though the CLI still works. Because archiving stamps
rows that are already stored, `offers_db.jsonl` is written atomically (temp file + swap) — it
is no longer append-only. Every run — the button *and* the two CLI harvesters — records itself
in `data/last_harvest.json` + `data/harvest_log.jsonl` via `common.log_run`, so the page can
never show fewer offers than the cockpit holds. A CLI run sweeps one portal, so its row is
tagged **partial**: its `live` and `expired` columns speak for that feed alone.

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
| `harvest.py` | Fetches justjoin.it into `data/offers_db.jsonl`. |
| `harvest_pracuj.py` | Fetches pracuj.pl into the same file, same row shape. |
| `common.py` | Shared stdlib helpers (Chrome UA, UTF-8, stable offer id, `merge`). |
| `migrate_offer_ids.py` | Re-keys the stored rows after an identity change and folds the duplicates. Dry run unless `--apply`. |
| `test_identity.py` | What must and must not collapse into one offer, plus the source lifecycle. `python finder/test_identity.py`. |
| `data/offers_db.jsonl` | Every offer ever seen; one line per unique job. Rows are never deleted — gone-from-the-feed ones carry `archived_at`. |
| `data/company_aliases.json` | Hand-written company spellings → the name to use. Merges *and* renames; see Identity & dedup. |
| `prototype/` | **The scorer + review page.** `keywords.py` is the file you tune. |

## Two portals, one database

The scorer and the cockpit are portal-agnostic — they read `title` and `skills`, which both
harvesters produce — so pracuj needed no change to either. What it did need:

- **A per-offer portal marker.** Every row in the cockpit carries a small `j` / `p` / `jp`
  badge: justjoin, pracuj, or *both*. `jp` is not a duplicate — it is one record whose two
  portal links are listed side by side in the expanded detail. There are currently ~330. It was
  ~110 until the identity key stopped treating `Sp. z o. o.` and `Sp. z o.o.` as two employers.
- **Per-source expiry.** A harvest of one portal is evidence about that portal only. So
  `archived_at` is stamped on the **source**, and the offer expires only when every source
  has it. Without that, harvesting justjoin would archive every pracuj offer, and vice versa.
- **A sanity floor.** Both harvesters refuse to merge a full run that comes back implausibly
  small. Archiving is what a full harvest licenses, so a broken fetch returning zero offers
  would otherwise expire the entire database while printing a perfectly normal summary.

pracuj's category comes from its own `its` specializations (backend / fullstack / it-admin /
…), so its categories sit *alongside* justjoin's language-shaped ones (net / python / java)
rather than replacing them. Offers pracuj's taxonomy never placed get `it-other` (~380).

### Where pracuj's data comes from

pracuj has a real backend API — `POST massachusetts.pracuj.pl/jobOffers/listing/grouped` — but
it answers **401** to anonymous callers (browsing cookies are not enough; the token is issued
elsewhere). We don't need it: every listing page ships the server's own answer to that call
embedded in its `__NEXT_DATA__` blob, no auth required. `?pn=` pages it, `?rop=200` is
honoured, and pagination counts `groupedOffersTotalCount` — the *other* count
(`offersTotalCount`) counts each city copy separately and would page ~20 times past the end.

That blob is app state, not a published interface, and it has already moved once
(`props.pageProps.data.jobOffers` → `dehydratedState.queries[]`). Hence the loud `sys.exit` at
every step of `job_offers()`: the dangerous failure is not a crash, it is HTTP 200 with zero
offers.

## Identity & dedup

- An offer's `id` = hash of normalized **title+company** — deliberately without the source
  site, so the same job harvested from justjoin *and* pracuj.pl collapses into one record
  carrying both links. Per-city clones collapse the same way (cities are unioned) — needed on
  both portals, since pracuj publishes a multi-city job as several groups too.
- **Normalized means reduced to a key, not just lowercased.** The portals disagree about
  spelling constantly (`LUX MED Sp. z o. o.` / `LUX MED Sp. z o.o.`, `Comarch SA` / `COMARCH`,
  `(k/m)` / `(m/k)`, and stray zero-width characters inside titles), and each disagreement used
  to fork one job into two records — which defeats the whole point of a site-less id. So
  `norm_company` strips case, punctuation, diacritics and legal forms, `norm_title` strips
  gender markers, and both run *before* the hash. The raw strings stay on the row for display.
  `clean_text` sanitizes at ingest so invisible characters never reach the db in the first
  place. See `test_identity.py` for exactly what must and must not collapse.
- `data/company_aliases.json` — `{"any spelling": "the name to use"}`. The escape hatch for what
  a mechanical normalizer cannot know (a rebrand, `Grupa X` vs `X`). The value's key replaces
  the entry's key, so it merges *and* sets the display name. An entry whose value keys the same
  is display-only (`{"COMARCH": "Comarch"}`); one that keys differently changes ids.
- **`python finder/migrate_offer_ids.py`** — re-key the stored rows and fold the new
  duplicates. Needed whenever the normalizer or the alias file changes, because rows on disk
  keep the id they were harvested with. Dry run by default; `--apply` backs up first. It
  refuses outright if a merge would drop a URL you have already applied through.
- One offer can hold **several links per portal** — a re-post under a new slug, one posting per
  city. All are kept: an application filed through any of them still has to count. A link the
  feed no longer carries gets `archived_at` on that source even while the offer stays live, so
  the cockpit links somewhere that still works; the offer expires only once every link has.
- Anti-double-apply now lives in the cockpit, not in a script: every offer carries a live
  **applied** status joined from `src/applications_log.jsonl` (bot) and `manual_applied.json`
  (you), so you skip the ones already done when you pick. It is a human-in-the-loop check, not
  the old automatic set-filter — the deprecated `legacy/build_worklist.ps1` did that. The join
  is over **every** URL the offer has ever had, not the one currently displayed — otherwise a
  job whose applied-through link expires reappears as untouched and gets applied to twice.

## Gotchas (learned the hard way — do not rediscover)

- The API 403s non-browser User-Agents (Cloudflare). All scripts send a Chrome UA.
- `itemsCount` paginates, `cursor` lies, `itemsPerPage` is ignored
  (see `..\docs\JUSTJOIN_API_NOTES.md`).
- pracuj's `salaryDisplayText` is free text and usually empty, its `positionLevels` are Polish
  sentences (only the `(junior)` / `(mid / Regular)` parenthetical is stable), and it has no
  analog of justjoin's `applyMethod` — so pracuj rows carry `apply_method: ""` (unknown) plus
  a raw `one_click` flag, rather than a guessed value.
- Everything is UTF-8 explicitly — Windows Python defaults to cp1250 and mangles
  Polish city names silently.
- `experienceLevel` and `category` are set by employers and lie routinely; the scorer leans
  on title/skill keywords, not the labels.
