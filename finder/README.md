# Finder — how it works and how to run it

Collects every junior+mid offer from **justjoin.it** and **pracuj.pl** and ranks them so the
good ones are easy to find. Two steps, both deterministic Python — no LLM, no browser, no
Cowork. Plain terminal in the project root.

## The pipeline

```
1. harvest.py          CODE  justjoin API   -> data/offers_db.jsonl (facts; adds new, archives gone)
   harvest_pracuj.py   CODE  pracuj listing -> the same file, same row shape
2. app.py       CODE  serves the cockpit: joins offers_db + bot log + your manual
                      marks + the queue, groups by company
3. (you) review the cockpit, click 1-2 per company into the queue — no "write" step,
                      each click is a server write to runner/data/worklist.json
4. runner/run_batch.py drains that queue at 23:00, appends to applications_log.jsonl,
                      and removes each offer once it has a log line
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

# 2. Start the cockpit, then open http://127.0.0.1:9000
python finder\app.py
```

The **↻ Harvest** button in the cockpit runs *both* portals in one go, which is the normal
way to do it — the CLI scripts exist so a single portal can be re-pulled or debugged alone.

The **cockpit** (`app.py` + `page.html`) is the one place you look. Offers are grouped by
company; a company with many openings is flagged so you review and pick the best 1–2 instead
of spraying CVs. Click any row to expand what happened — the CV used, the free-text the bot
entered, the outcome, the full notes. Each offer carries a live status: **bot** (from the
append-only log) or **applied by me** (your manual toggle). No file downloads.

## Picking: one button, three states, no "write" step

```
(empty) --click--> queued --click--> queued + dig deeper --click--> (empty)
   ☐                 ✓                      ✓🔎                        ☐
```

Every click is a POST that lands on disk before the row redraws, so picks survive a refresh, a
restart and a week. **Queued** appends to `runner/data/worklist.json` — the apply queue the
nightly runner drains. **Dig deeper** additionally files the offer in `data/dig_deeper.json`,
the list you work by hand (find the company's email, write to a human); it stays queued for the
bot as well. State is read back off both files on every request, so a second tab, a refresh, or
the runner deleting from the queue overnight all agree.

The state is joined on **every** URL an offer has ever had, the same as applied-status — so a
job posted on both portals (`jp`) queues once, and shows as queued whichever portal link the row
happens to display.

Applied offers show no pick button at all.

## The right-hand panel

The empty space right of the list is now a sticky two-tab panel:

- **Queue (N)** — the whole queue in run order, with a divider marking the nightly `--limit`;
  everything below it is dimmed and waits for the next night. Each row is the offer's link
  (title first, company under it) and carries a `×` to unqueue. The footer carries the
  schedule, both ways to run it by hand, and a **last batch** line read from
  `runner/data/batch_log.jsonl` — which is how you tell in the morning whether last night ran.
  The two commands are one run spelled twice: `--mode auto` (what the nightly task does:
  fills and submits) and `--mode review` (fills everything, stops before the final Submit).
- **Dig deeper (M)** — the same rows, each with its outreach **stage** chip and a `✓` once
  contacts are found; a row opens its card on `/outreach` (see [Outreach](#outreach) below).
  **Copy as markdown** produces `- [ ] Company — Title — url — email — note` lines to paste
  anywhere. Dropping a card that holds contacts or a draft — by `×` or by the pick cycle —
  asks first.

The **queue** is drag-sorted by the `⠿` grip on the left of a row (only the grip starts a drag;
the rest of the row is a link). A drop POSTs the new order to `/api/queue/reorder`, which
rewrites `worklist.json` in that order — so a drag decides what tonight's `--limit` reaches.
It applies the order to the file on disk, never to the copy the page was holding: the runner
deletes from the queue while you drag, and what it dropped stays dropped.

The **dig list has no drag of its own**: `/api/dig` serves it in queue order, so both tabs read
the same top-down and one drag decides both. Dig entries the runner has already drained off
the queue keep their file order, behind the queued ones.

The panel re-fetches after every pick and on load, so a queue the runner changed mid-evening
never goes stale.

There is no automatic picker any more. `auto_worklist.py` chose five offers every hour and
rewrote the worklist; a queue you build by hand over days cannot survive that, so it and its
Windows task are gone. Deciding which offers to apply to is the one step that stays human —
the only automation left is the 23:00 drain.

Every expanded offer also carries a **Copy prompt** button: a ready-to-paste, single-offer
Cowork prompt (read `applier_instructions.md` + `profile.md`, run mode `review`, this offer's
JSON inline). It's the orchestrator's per-subagent task for one offer — paste it into a fresh
Cowork agent to apply to just that offer without going through `worklist.json`.

The **↻ Harvest** link in the header opens a dedicated subpage at **`/harvest`** with one
button that re-pulls **both live feeds**. **Nothing is ever deleted:** an offer that fell off a
feed is stamped `archived_at` on *that portal's* source entry, and only counts as expired once
every portal carrying it has dropped it; one that reappears has the stamp cleared
(`revived_at` records when). The subpage shows tiles (`+new`, expired, revived, in db, live,
archived-total), a table of recent runs, and everything that came in on the last run — the same
expandable row as the cockpit (click the ☐ to queue, click to open, mark applied, adjust the
score, copy the apply prompt), rendered by `static/offer.js` + `static/offer.css`, which both
pages link so the row cannot drift between them.

Those arrivals are **grouped by company**, the cockpit's grouping turned around: one block per
company the run touched, showing *only* its new offers. The header answers what a new posting
actually raises — `+N new`, how many offers the company has live, and `✓ applied N` if you have
already been in touch. Click it to unfold the company's other offers (score-sorted, each with
its own applied status); expired ones are left out unless you applied to them, since a dead link
you already answered is the part of the history that matters. Picking here posts to the same
queue as the cockpit's, so a run's picks go in without a detour — the header shows how many are
queued; the panel itself lives on the cockpit.
`GET /api/harvest` returns only the run stats — the offers come from `/api/offers`, whose
`is_new` flag is the single definition of "came in on the last run".
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

Five files, joined by offer URL (plus `data/outreach_sent.jsonl`, append-only, for the `✉`):

| file | who writes it | how |
|---|---|---|
| `data/offers_db.jsonl` | `harvest.py` / Re-harvest | atomic rewrite (temp + swap): adds new rows, stamps `archived_at` on vanished ones |
| `../runner/data/applications_log.jsonl` | `runner/run_batch.py` | append-only (crash-safe) |
| `data/manual_applied.json` | you, via the cockpit | mutable dict, toggle on/off |
| `../runner/data/worklist.json` | **both** the cockpit and the runner | read-modify-write, `.tmp` + `os.replace` on each side |
| `data/dig_deeper.json` | the cockpit, `/outreach`, agents, `send_outreach.py` | read-modify-write, `.tmp` + `os.replace`; never written while it does not parse |

The queue and the dig cards are the files with several writers: you add to the queue while the
runner deletes from it, and you edit cards while an agent fills them and the sender removes the
ones it mailed. So no side ever writes a list it was holding — each re-reads, changes one entry
and swaps the file in atomically. A whole-file overwrite from a stale copy would silently erase
the other side's work.

**Superseded:** `prototype/browse.py` (static triage page, applied-state in localStorage) and
the whole `legacy/` PowerShell pipeline (`harvest_offers.ps1` + `build_worklist.ps1` +
`offers_queue.json`). The cockpit does harvest, triage and worklist-writing, backed by the real
log instead of the browser. The legacy files are frozen for reference (`legacy/README.md`).

Tuning loop for scoring: edit `prototype\keywords.py` → restart `app.py` → refresh the tab.

## Outreach

Each dig-deeper offer is a **card** in `data/dig_deeper.json`, and the card is the whole
outreach: contacts, the email, your approval. It fills up in stages:

```
 no contact  ──►  contacts ✓  ──►  draft  ──►  approved  ──►  sent → leaves the list
               (email / other)   (subject +   (you clicked     (logged with its text in
                                  body)        OK to send)      outreach_sent.jsonl)
```

**`/outreach`** (the `✉ Outreach` link in the cockpit header) lists the cards furthest along
first — approved (sendable before held), complete drafts, drafts still missing something,
contacts only, nothing yet; queue order within each — with a stage filter, and edits one at a
time: email, other contacts, subject, CV, body, notes. The cockpit's dig tab uses the same order.
It shows whether the offer's application actually went out, and what would stop the email.
It re-reads the file whenever you come back to the tab.

**OK to send** stores a *stamp* on the card: a short hash of the email + subject + body + CV
(after the fallback below). Change a single letter of those afterwards — on the page or in the
file — and the stamp no longer matches: the card is back at `draft` ("approval stale") and will
not be sent. Nothing watches for edits; the sender checks the stamp right before each send.

The **CV** defaults to the one the bot attached to this offer's application (`cv_used` in the
log), so the email and the application match. Pick another in the dropdown to override it.

**Sending** is `send_outreach.py`. The **✉ Send approved** button on `/outreach` runs it with
`--send` for the ready cards it lists in its confirm (at most 5, `--url` each, in page order),
as a child of `app.py` — keep the server running until it finishes; its output shows under the
button and stays in `data/outreach_send.log`. The same command by hand:

```powershell
python finder\send_outreach.py                        # dry run: READY, or why not, per card
python finder\send_outreach.py --send                 # up to --max 5, --pause 120-300 s apart
python finder\send_outreach.py --send --test-to you@gmail.com --max 1 --only soneta
```

It needs a Gmail App Password. Set it once as a user variable and both the button and the
command find it, without restarting anything (the sender reads it from the registry):
`[Environment]::SetEnvironmentVariable("GMAIL_APP_PASSWORD", "xxxx xxxx xxxx xxxx", "User")`.

A card is **READY** when it has a valid email, subject, body and a CV on disk, its approval
stamp matches, this (offer, address) pair is not in the sent log, and the offer's application
went out — the bot logged a sent outcome through any of its links (`filled_review` counts), or
you marked it applied by hand. A `blocked` application, or none at all, **holds** the email:
the drafts say "I already applied", so submit it and tick "I applied by hand" first. The page
says so only in the application line and a `held` flag in the list, not in a box. Each email logs in to SMTP anew (Gmail drops a connection idle for minutes), the first
SMTP error stops the run, and a card edited during a pause is re-judged and skipped.

For every email that leaves: the line goes into `outreach_sent.jsonl` first (with the body and
a copy of the card), then the card is removed from `dig_deeper.json` — re-read, one key dropped,
atomic replace, so a click or an agent's edit made during the pause survives. A run that dies in
between finishes the removal next time. The cockpit keeps a `✉` on the offer's row, and so
does `/history`: the email is not a row of its own there but part of the offer's application
row, word for word when you open it.

`--test-to` sends the real email to you, subject prefixed with the address it would have gone
to. It skips the approval and application checks — nothing reaches the employer — and logs and
removes nothing.

### For agents

You are filling outreach cards in `finder/data/dig_deeper.json`, an object of offer URL → card.
Edit the file in place; the page and the sender pick your edits up on their own.

- `email` — **one** address, the one the email goes to. Nothing else in this field.
- `other` — free text for everything else: the person's name and role, a second address,
  phone, LinkedIn, where you found it (`site` / `search`). Nothing parses it.
- `subject` — one line.
- `body` — sent **verbatim**, so it is the finished email: one line per paragraph (the
  recipient's client wraps them), a blank line between paragraphs, the signature included.
- `cv` — optional, `src/CV_PDF/<variant>/<file>.pdf`. Leave it empty to attach the CV the bot
  used for this offer's application.
- `note` — the owner's notes; add to it, don't replace it.
- **Never write `approved`.** It is the owner's approval of the exact text, set only by the
  page's OK-to-send button. Any edit you make to `email`, `subject`, `body` or `cv` voids an
  existing one, which is intended: the owner reads the new version before it goes out.
- Keep the file valid JSON. A broken file is refused by the page and the sender until fixed.
- Facts about the owner come only from `src/profile.md`; never invent experience or claims.

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
| `data/dig_deeper.json` | The outreach cards: `{url: card}`, one per dig-deeper offer, with its contacts and email draft. Not in `src/` — the applier must never pay tokens for it. |
| `outreach.py` | The card rules (stage, approval stamp, problems, held), shared by `app.py` and the sender. A library, no CLI. |
| `outreach.html` | The `/outreach` page: the card list and its editor. |
| `send_outreach.py` | Sends approved cards over Gmail SMTP with the CV attached from disk (the Gmail connector can't attach a real file). Dry run unless `--send`; needs `GMAIL_APP_PASSWORD`. |
| `data/outreach_sent.jsonl` | One line per email that left, with its full text and a copy of the card; an (offer, address) pair in it is never sent twice. `/history` reads it. |
| `data/outreach_send.log` | The last ✉ Send run's output, shown under the button on `/outreach`. Overwritten by the next run. |
| `data/*_2026-09-10.md` | The first batch's contacts report and drafts, from before the cards existed. Kept as the record; nothing reads them. |

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
  **applied** status joined from `runner/data/applications_log.jsonl` (bot) and `manual_applied.json`
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
