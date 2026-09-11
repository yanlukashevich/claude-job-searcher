# CLAUDE.md

Guidance for Claude Code sessions opened at the **project root**. Read `ARCHITECTURE.md` for
the design; it is the source of truth.

## What this is

An **auto job applier**: it applies to jobs on justjoin.it and pracuj.pl on behalf of Yan
Lukashevich by driving his real, logged-in Chrome. There is almost no conventional code — the
markdown files under `src/` *are* the program. Claude Code is the runtime, Claude-in-Chrome
(MCP) is the browser engine. Currently **Phase 1** (justjoin.it internal-modal + external ATS,
review mode) per `ARCHITECTURE.md` §6.

## Layout — the `src/` boundary is load-bearing

`src/` is the applier's working directory and the only folder it has any business in. The
boundary used to be a Cowork mount; it is now the launch line in `runner/run_batch.py`
(`--setting-sources ""`, `--tools Read Glob`, `cwd=src`), which injects no `CLAUDE.md` and
hands the agent no way to write at all. The layout still matters, for a different reason:
every token in `src/` is paid once per offer.

```
claude_job_seracher/          <- outside the applier's working directory
  CLAUDE.md  ARCHITECTURE.md  README.md
  finder/                     <- offer collection + triage + worklist (Python cockpit)
  runner/                     <- run_batch.py: launches one applier per offer, writes the log
    data/                     <- worklist.json, applications_log.jsonl, todo_manual.md
  docs/                       <- JUSTJOIN_API_NOTES.md and design notes
  legacy/                     <- frozen, superseded PowerShell pipeline
  trainer/                    <- prompt-optimization loop (its own Cowork mount)
  src/                        <- the applier's cwd; prompts and CVs only, nothing it can act on
    applier_instructions.md   profile.md
    portal_quirks.md   ats_quirks.md   CV_PDF/
```

`--tools Read Glob` means the applier *can* read anything it can reach, so keeping the finder's
offer database out of `src/` still does work — but it is now a token and attention argument,
not a wall. **Keep it that way** — a file moved into `src/` is a file the agent will find,
and every extra token in there is paid once per offer.

`portal_quirks.md` and `ats_quirks.md` are the pressure valve for that last rule. Per-form
recipes are long and each is needed on a minority of offers, so carrying them in the playbook
would charge every offer for them. Instead every offer ends up on **exactly one** kind of form —
the portal's own (justjoin modal, pracuj widget) or an external ATS — so the applier classifies
first and opens **one** of the two files. Anything true of one vendor's form and not of forms in
general belongs in one of them, not in the playbook. Keep them split for the same reason: merged,
a portal offer would pay for Workday recipes it will never use.

The queue and the audit trail live in `runner/data/`, not in `src/`, and that is what keeps the
playbook free of rules about them. Code writes and reads both; the applier is handed its one
offer in the task prompt and returns a JSON object. When `worklist.json` sat in the applier's
cwd it had to be told "never read it" — and a log in reach still pulled appliers into checking
for duplicates themselves. Out of reach, neither line has to be written or paid for per offer.
`finder/data/dig_deeper.json` is out of reach for the same reason: it is your outreach list,
and nothing the applier does depends on it.

## The two-brain split (do not merge these)

- **`src/profile.md` — the FACTS.** Sole source of truth for every factual answer. On a
  factual conflict, this file wins.
- **`src/applier_instructions.md` — the BEHAVIOR.** The playbook: form filling, free-text, the
  per-offer loop, block rules, logging schema. On how to behave, this file wins.

**Never invent hard facts** (experience, salary, work-auth, certs, dates). A required field
needing an absent hard fact is a *block*, not a guess.

## Running it

**Pick continuously, the runner drains nightly.** Offer selection is a human review in the
finder; applying is the agent, on a schedule.

```powershell
# 1. FINDER - harvest, score, pick. See finder/README.md.
python finder\app.py                 # open http://127.0.0.1:9000, hit "↻ Harvest" (both portals),
                                     # review, click offers into the queue on the right
```

Both portals land in one `offers_db.jsonl`; the same job on both collapses to one row carrying
both links, marked `jp` in the cockpit. The CLI harvesters (`harvest.py`, `harvest_pracuj.py`)
re-pull a single portal when one needs debugging.

The cockpit shows each offer's **applied** status (bot log + your manual marks), so you pick the
unapplied ones. The pick button cycles through three states, each click a server write:

```
(empty) --> queued --> queued + dig deeper --> (empty)
```

**Queued** = written to `runner\data\worklist.json` immediately; it survives refreshes and
outlives the session, and the right-hand panel shows the whole queue with a divider marking
tonight's `--limit`. **Dig deeper** = also filed in `finder/data/dig_deeper.json`, the list you
work by hand (find the company's email, write to a human) — additive, the bot still applies
through the portal. The throttle is the nightly `-Count`, not how many you click.

```powershell
# 2. RUNNER - one applier per offer, sequentially. See runner/README.md.
powershell -File runner\register_nightly.ps1 -Count 3   # 23:00 daily, --mode auto. ONCE.
python runner\run_batch.py --dry-run                    # print the queue and the launch line
python runner\run_batch.py --mode review                # fill everything, stop before Submit
python runner\run_batch.py --mode auto --limit 10       # what the nightly task runs
```

`run_batch.py` reads `runner\data\worklist.json` (never re-filters it), brings up the
`chrome-mcp` profile if CDP port 9222 is silent, and runs one `claude -p` per offer with
`cwd=src`. The applier reads `applier_instructions.md` + `profile.md`, drives one application,
and **returns** a JSON object matching `runner/log_line.schema.json`; the runner stamps the
time and writes `runner\data\applications_log.jsonl` and, for a blocked offer,
`runner\data\todo_manual.md`.

Then it **removes the offer from the queue** — tied to the log line, not to success, because
`blocked` and `filled_review` are attempts too and must not be repeated (`--keep` opts out).
Offers the batch never reached stay queued, which is the whole design of the **usage-limit**
rule: on a quota wall the batch stops without writing a log line, so nothing is marked
attempted, nothing is removed, and `main()` exits **2** so Task Scheduler records the failed
night. Each batch appends one summary line to `runner\data\batch_log.jsonl`, which is what the
cockpit panel shows as "last batch".

- **Sequential, never parallel** — two appliers would fight over the same Chrome tab. The
  scheduled task is registered `-MultipleInstances IgnoreNew` for the same reason.
- The nightly task runs **in your session**, so the machine must be awake and logged on at
  23:00; that is also why Windows never stores a password.
- The hourly machine-picker (`finder/auto_worklist.py` + its Windows task) is **deleted**:
  it rewrote `worklist.json` every hour at :40, which a hand-picked persistent queue cannot
  survive. Picking is a human act now, and the only automation is the 23:00 drain.
- The browser has a **second** permission gate no CLI flag reaches: the extension asks before
  touching a domain it has not seen, which is every employer ATS. `run_batch.py` starts
  `runner\permission_autoclick.py` to click that card and kills it when the batch ends
  (`--no-autoclick` opts out; approvals go to `runner\data\autoclick.log`). ARCHITECTURE.md §5E.
- `review` (default) = fill everything, **stop before final Submit**. `auto` = fill and submit.
- The CV is attached by `tools/mcp_webfile` over raw CDP; `mcp__chrome__file_upload` is not in
  the applier's toolset at all. That is why Cowork is no longer required.

## Data flow

```
finder/harvest.py + harvest_pracuj.py  →  finder/data/offers_db.jsonl   (every offer ever seen)
   → finder cockpit (app.py)  CODE: score + join applied-status; you click
      → runner/data/worklist.json      the QUEUE — persistent, added to one click at a time
      → finder/data/dig_deeper.json    the outreach list (second click; you work it by hand)
         → runner/run_batch.py  (trusts the queue, never re-filters), 23:00 via runner/nightly.ps1
            → one fresh `claude -p` per offer  (applier_instructions.md + profile.md)
               → applies via Claude-in-Chrome, attaches the CV via mcp_webfile
               → returns one JSON object  (runner/log_line.schema.json)
                  → runner/data/applications_log.jsonl  (append-only audit trail)
                  → runner/data/todo_manual.md          (blocked offers only)
                  → runner/data/run_log.jsonl           (per-launch diagnostics)
                  → then the offer is removed from worklist.json
            → runner/data/batch_log.jsonl              (one line per batch)
```

`applications_log.jsonl` is the anti-double-apply record: the cockpit joins it back onto the
offer list so already-applied offers are visibly marked. The old set-based dedup lived in
`legacy/build_worklist.ps1` (frozen). A **missing** line is the one unacceptable outcome, so an
applier that dies, times out or returns nothing still gets one — written by the runner as
`blocked` / `applier-failure`.

## Editing the prompts

The markdown in `src/` is the program, and its token count is paid once per offer. The full
working note is `docs/PROMPT_EDITING.md` — hand it to a session that is about to edit a prompt.
Two rules, both learned the hard way:

- **Keep a line if removing it would change what the agent does; cut it if removing it would
  only change what the agent knows.** A warning the agent cannot act on is documentation — it
  belongs in this file, not in `src/`.
- **A bare prohibition names a symptom; the reason kills the cause.** "Don't read the log"
  blocks one filename, while the underlying impulse ("I should check for duplicates") simply
  routes around it. State the reason in one clause, then the rule — not a paragraph of
  architecture.

## Detail lives in `src/`, not here

The four "stop → manual" blockers, the anti-bot interaction model, the language rule, the
CV-variant mapping and the logging schema are specified in `src/applier_instructions.md` §8,
§4, §6, §7 and §10. Restating them here is how this file grew to 6 KB last time.
