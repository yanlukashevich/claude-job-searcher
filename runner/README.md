# runner — launches the applier

Replaces the Cowork orchestrator. See `docs/COWORK_TO_CLAUDE_CODE.md` for why.

```powershell
python runner\run_batch.py --dry-run          # print the queue and the exact command
python runner\run_batch.py --mode review      # fill everything, stop before Submit (default)
python runner\run_batch.py --mode auto --limit 5
```

The applier runs on **sonnet** (`--model`, override per run). `--limit N` takes the first N
offers; `--pick` takes the ones you name, by 1-based worklist position: `--pick 1`, `--pick 3-5`,
`--pick 2,4`. That is how one worklist gets split across several runs with different modes.

## What it does

Reads `data\worklist.json` (trusts it — no filtering, no re-sorting) and, **sequentially**, runs
one `claude -p` per offer with `cwd = src\`. Two appliers at once would fight over the same
Chrome tab, so never parallelise this.

Chrome comes up first: it checks `127.0.0.1:9222/json/version` and, if silent, detaches
`tools\mcp_webfile\start_chrome.ps1` and waits for the port.

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

`runner\data\run_log.jsonl` gets one line per launch: exit code, duration, cost, session id,
failure. Gitignored; it is diagnostics, not the audit trail.

## Why the queue and the log live in `runner\data\`

They are code's files: the cockpit writes the worklist and reads the log back for applied-status,
the runner does the reverse. The applier touches neither — it is handed one offer in its prompt
and returns JSON. They used to sit in `src\` (the applier's cwd), which cost a "never read
`worklist.json`" line in the playbook, paid once per offer, and still left a log in reach for an
applier that decided to check for duplicates itself. Out of the cwd, the rule is unnecessary.
