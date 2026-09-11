# runner — launches the applier

Replaces the Cowork orchestrator. See `docs/COWORK_TO_CLAUDE_CODE.md` for why.

```powershell
python runner\run_batch.py --dry-run          # print the queue and the exact command
python runner\run_batch.py --mode review      # fill everything, stop before Submit (default)
python runner\run_batch.py --mode auto --limit 10
```

The applier runs on **sonnet** (`--model`, override per run). `--limit N` takes the first N
offers; `--pick` takes the ones you name, by 1-based queue position: `--pick 1`, `--pick 3-5`,
`--pick 2,4`. That is how one queue gets split across several runs with different modes.

## What it does

Reads `data\worklist.json` (trusts it — no filtering, no re-sorting) and, **sequentially**, runs
one `claude -p` per offer with `cwd = src\`. Two appliers at once would fight over the same
Chrome tab, so never parallelise this.

Chrome comes up first: it checks `127.0.0.1:9222/json/version` and, if silent, detaches
`tools\mcp_webfile\start_chrome.ps1` and waits for the port.

## The worklist is a queue

You add to `data\worklist.json` one click at a time in the cockpit, over days; this drains it.
An offer is removed **as soon as it has a log line** — `applied_*`, `filled_review` and
`blocked` alike, because all three are attempts and re-applying to them is exactly what the
queue prevents. `--keep` leaves the file alone for a run.

`consume()` re-reads the file before every removal and replaces it atomically (`.tmp` +
`os.replace`, the same as `finder/app.py`). You can keep clicking offers into the queue while a
batch runs; a whole-file write from a stale in-memory copy would erase them.

## The usage limit stops the batch, not the queue

A quota wall has no dedicated CLI subtype. It surfaces as `subtype: "error_during_execution"`
with the human sentence in a top-level `errors: []` array, so `envelope_meta()` keeps that field
and `hit_usage_limit()` matches it against `LIMIT_MARKERS` (plus `api_error_status == 429` and
`subtype == "error_max_budget_usd"`) across stdout, stderr and `errors`.

On a match the batch **breaks immediately**: no application log line, so the cockpit never marks
the offer attempted, and no `consume()`, so it is first in line tomorrow night. `main()` returns
**2**, which is how Task Scheduler tells a stopped night from a finished one. Without this, a
wall burned every remaining offer as `blocked / applier-failure` — which the cockpit reads as
"already attempted", quietly poisoning them.

Testing it does not require waiting for a real wall:

```powershell
$env:RUNBATCH_FAKE_LIMIT=2
python runner\run_batch.py --mode review --limit 3     # offer 2 hits the sentinel
```

## Nightly

```powershell
powershell -File runner\register_nightly.ps1 -Count 3    # register; -Now fires it once
powershell -File runner\register_nightly.ps1 -Unregister
```

`JobSeracher-NightlyApplier` runs `nightly.ps1` at 23:00 daily: it appends a dated block to
`data\nightly.log`, exits early if the queue is empty, runs `--mode auto --limit <Count>` and
records the exit code (0 finished, 1 nothing to do, 2 stopped on the usage limit).

**`--mode auto` really submits.** Register with `-Count 3` for the first week and read
`data\nightly.log` in the morning; three unattended submissions is a cheap way to find out
whether the autoclick and the Chrome preflight hold up overnight before trusting it with ten.

The task runs **in your session** — so the machine must be awake and logged on at 23:00, and
Windows never has to store a password. `-MultipleInstances IgnoreNew` keeps a long batch from
being joined by the next night's. The 4-hour limit is sized off real runs (222 s / 335 s / 615 s
per offer in `run_log.jsonl`) against the 900 s per-offer timeout: ten offers cannot exceed
~2.5 h, so it only fires on something genuinely wedged.

There is no second scheduled task. The hourly `JobSeracher-AutoWorklist` picker was deleted
along with `finder/auto_worklist.py` — it rewrote the queue every hour at :40, which a
hand-picked queue cannot survive.

## The browser's second permission gate

The Chrome extension keeps a per-domain allowlist of its own, and no CLI flag reaches it — not
`bypassPermissions`, which only opens Claude Code's door. On a domain it has not seen (i.e. every
employer ATS) it draws a card in the browser and *waits* for a click, so an unattended offer ends
as a block. See ARCHITECTURE.md §5E for the measurements.

`run_batch.py` starts `permission_autoclick.py` before the queue and kills it in a `finally`, so
the standing consent lasts exactly one batch — Ctrl-C and crashes included. Approved hosts are
appended to `data\autoclick.log`. `--no-autoclick` turns it off and you click the cards yourself.

```powershell
python runner\permission_autoclick.py --discover   # dialog on screen? show what it can see
python runner\permission_autoclick.py              # watch and click, until Ctrl-C
```

It only touches pages belonging to the Claude extension, only a control whose visible text matches
*Always allow actions on this site*, and only when the page also carries the card's own wording. A
Submit button on a job form is outside what it can reach, by construction.

## The applier cannot write

```
--setting-sources ""     no CLAUDE.md, no user settings, no user-scope MCP servers
--mcp-config …           chrome + webfile - mandatory, since the line above dropped them
--tools Read Glob        built-ins only: no Write, no Edit, no Bash
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
```

Those four lines are what the Cowork mount used to do, and they do it better — explicit on the
command line instead of depending on which folder someone connected. Measured tool surface:
`Read`, `Glob`, 21 `mcp__chrome__*`, both `mcp__webfile__*`. Nothing else.

The prompt goes on **stdin**: `--tools` and `--mcp-config` are variadic and would eat a prompt
written after them.

## Who writes the log

The applier returns one JSON object matching `log_line.schema.json`; the CLI enforces the schema
and hands it back parsed as `structured_output`. The runner adds the timestamp from the Windows
clock (`Europe/Warsaw`) and appends the line to `data\applications_log.jsonl` — so the time is
real, a half-written line is impossible, and the on-disk format `finder/app.py` reads is
unchanged.

- `outcome == "blocked"` → also an entry in `data\todo_manual.md`.
- **Applier died, timed out, or returned nothing** → the runner still writes a line, with
  `blocked / applier-failure` and the tail of its output in `notes`. A missing line is the one
  unacceptable outcome: the log is the anti-double-apply record, so a gap means the next run
  applies twice.
- The url is taken from the worklist, not from the applier — the cockpit joins the log onto the
  offer list by url. A mismatch is recorded in `runner\data\run_log.jsonl`.

## Diagnostics: batch_log.jsonl, run_log.jsonl and stats.py

`data\batch_log.jsonl` gets one line per **batch** — `started`, `finished`, `mode`, `limit`,
`attempted`, `applied`, `review`, `blocked`, `aborted`, `cost_usd`, `queue_left`. Nobody is
watching stdout at 23:00 and `run_log.jsonl` is per-offer, so this is how you tell in the
morning whether the night ran at all and how it ended. The cockpit's queue panel reads its last
line as "last batch".


`runner\data\run_log.jsonl` gets one line per launch, taken from the CLI's result envelope: exit
code, wall clock, `duration_api_ms`, cost, the token breakdown (`tokens.cache_read` against
`tokens.cache_creation`), `stop_reason` / `terminal_reason`, `permission_denials`, and the
`session_id`. Gitignored; it is diagnostics, not the audit trail.

```powershell
python runner\stats.py                 # last 20 launches: table, aggregates, warnings
python runner\stats.py --offer apator  # one run in full: every tool call, every error
python runner\stats.py --json          # the joined rows, for anything else
```

`stats.py` joins that log to two things it already holds the keys for: `applications_log.jsonl`
by url (so cost groups by ATS vendor and apply_type) and, by `session_id`, the transcript the CLI
wrote to `~\.claude\projects\<cwd-slug>\<session_id>.jsonl`. The transcript is where the cost
spread actually comes from — tool-call histogram, screenshot count, tool errors, which files were
read, peak context. None of it costs a token or asks the applier for anything; it is all already
on disk.

Two numbers carry most of the weight. `duration_api_ms` against the runner's wall clock separates
a slow model from a slow browser. Screenshots per offer is the real cost driver — an offer with
nine of them costs about three times one with two, and `total_cost_usd` alone never says so.

The same numbers reach the cockpit's history page: opening a row there calls
`GET /api/run?url=&at=`, which is `stats.run_for` -- one launch, matched to that attempt by
nearest timestamp. It is fetched on the click, not with the list, because a transcript runs to
megabytes and most of the audit trail predates `run_log.jsonl` and has no run to show.

The warnings block is the point of the tool. It flags: both quirks files read on one offer (they
are split so each offer opens exactly one), a tool the playbook reached for that `--tools`
withheld, tool errors, peak context past 60% of the window, and an offer logged as applied where
`attach_file` was never called.

## Why the queue and the log live in `runner\data\`

They are code's files: the cockpit writes the worklist and reads the log back for applied-status,
the runner does the reverse. The applier touches neither — it is handed one offer in its prompt
and returns JSON. They used to sit in `src\` (the applier's cwd), which cost a "never read
`worklist.json`" line in the playbook, paid once per offer, and still left a log in reach for an
applier that decided to check for duplicates itself. Out of the cwd, the rule is unnecessary.
