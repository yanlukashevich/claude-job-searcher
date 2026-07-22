# claude_job_seracher — auto job applier

Applies to jobs on justjoin.it (later pracuj.pl) on behalf of Yan Lukashevich by driving his
real, logged-in Chrome. There is almost no conventional code — the markdown under `src/` *is*
the program, Claude-in-Chrome (MCP) is the browser engine, Cowork is the runtime.

**`ARCHITECTURE.md` is the source of truth for the design.** `CLAUDE.md` is the operating guide
for a Claude Code session opened at this root.

## The three subsystems

| Folder | What it is | Runs where |
|---|---|---|
| **`finder/`** | Collects offers from justjoin's JSON API, scores them, and serves a local **cockpit** where you review and pick. Writes `src/worklist.json`. | Plain Python, terminal |
| **`src/`** | The **Applier** runtime — the prompts + facts + logs that drive one application per offer. Cowork mounts *exactly this folder*. | Cowork (desktop app) |
| **`trainer/`** | A self-contained loop that optimizes the applier prompt (`candidate_applier.md`) against test offers. Its own Cowork mount. | Cowork (desktop app) |

The end-to-end flow:

```
finder/  →  src/worklist.json  →  Cowork orchestrator  →  one subagent per offer  →  applications_log.jsonl
(pick offers)                     (src/ mount)            (applies in Chrome, uploads CV)
```

## Supporting folders

- **`docs/`** — design notes, incl. `JUSTJOIN_API_NOTES.md` (the justjoin API's pagination
  traps — live reference for `finder/harvest.py`).
- **`legacy/`** — the original PowerShell collection pipeline, **frozen and superseded** by
  `finder/`. See `legacy/README.md`.

## Two things that look like duplication but aren't

Cowork mounts one folder and cannot see above it, so `src/` and `trainer/` each carry their own
copy of `profile.md`, `ats_quirks.md` and `CV_PDF/`. **Do not "consolidate" them** — the
isolation is the whole point. `trainer/` holds read-only training copies; `src/` holds the live
production files.

## Where to start

- Running the pipeline → `CLAUDE.md` ("Running it") and `finder/README.md`.
- The design and the decisions behind it → `ARCHITECTURE.md`.
- Tuning the applier prompt → `trainer/trainer_instructions.md`.
