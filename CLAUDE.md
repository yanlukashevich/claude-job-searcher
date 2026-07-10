# CLAUDE.md

Guidance for Claude Code sessions opened at the **project root**. Read `ARCHITECTURE.md` for
the design; it is the source of truth.

## What this is

An **auto job applier**: it applies to jobs on justjoin.it (later pracuj.pl) on behalf of Yan
Lukashevich by driving his real, logged-in Chrome. There is almost no conventional code — the
markdown files under `src/` *are* the program. Claude Code is the runtime, Claude-in-Chrome
(MCP) is the browser engine. Currently **Phase 1** (justjoin.it internal-modal + external ATS,
review mode) per `ARCHITECTURE.md` §6.

## Layout — the `src/` boundary is load-bearing

Cowork mounts **exactly one folder**, and that mount is a hard filesystem boundary: the agent
cannot see, read, or write anything above it. So the runtime files live in `src/`, and
everything the agent has no business touching stays out of it.

```
claude_job_seracher/          <- never mounted; invisible to the agent
  CLAUDE.md  ARCHITECTURE.md  build_worklist.ps1  offers_queue.json  old/
  src/                        <- Cowork mounts THIS
    orchestrator_instructions.md   applier_instructions.md   profile.md
    worklist.json  applications_log.jsonl  todo_manual.md  CV_PDF/
```

This replaces prose with geometry. `offers_queue.json` is out of reach, so nothing has to tell
the orchestrator not to read it; `CLAUDE.md` is out of reach, so it is not injected into every
subagent. **Keep it that way** — a file moved into `src/` is a file the agent will find, and
every extra token in there is paid once per subagent.

`applications_log.jsonl` is the exception. It is an *output*, so it must be inside the mount,
and the orchestrator must read its last line to verify each outcome. That rule is conditional
on purpose — forbidden for dedup, required for verification — so no folder layout can encode
it, and it stays as prose in `orchestrator_instructions.md` §1 and §5.

## The two-brain split (do not merge these)

- **`src/profile.md` — the FACTS.** Sole source of truth for every factual answer. On a
  factual conflict, this file wins.
- **`src/applier_instructions.md` — the BEHAVIOR.** The playbook: form filling, free-text, the
  per-offer loop, block rules, logging schema. On how to behave, this file wins.

**Never invent hard facts** (experience, salary, work-auth, certs, dates). A required field
needing an absent hard fact is a *block*, not a guess.

## Running it

Two steps. Deterministic work lives in code; reasoning lives in the agent.

```powershell
# 1. CODE - filtering, dedup, caps. Reads offers_queue.json, writes src\worklist.json.
.\build_worklist.ps1 -Limit 1        # careful first run: 1 offer
.\build_worklist.ps1                 # whole queue, bounded by -DailyCap (default 12)
.\build_worklist.ps1 -DryRun         # print the selection, write nothing
```

**2. PROSE** — open the **Claude desktop app (Cowork)**, connect the **`src/` folder** (not the
project root), and give it `orchestrator_instructions.md` as the task. It reads `worklist.json`
and spawns one fresh subagent per offer, each reading `applier_instructions.md` + `profile.md`
and driving one application.

- **It must run in Cowork, not the CLI.** Only Cowork's `claude-in-chrome` server can attach a
  CV (reads the file host-side → base64); the CLI forwards raw paths, which the extension
  rejects. `old/run_applier.ps1` is deprecated and will silently fail to attach a CV.
- `review` mode (default) = fill everything, **stop before final Submit**. `auto` = fill and
  submit.

## Data flow

```
offers_queue.json  (Finder output)
   → build_worklist.ps1   CODE: status:pending + dedup vs log + -Limit + -DailyCap
      → src/worklist.json
         → Cowork orchestrator  (trusts worklist, never re-filters)
            → one fresh subagent per offer  (applier_instructions.md + profile.md)
               → applies via Claude-in-Chrome, uploads CV
                  → applications_log.jsonl   (append-only audit trail)
                  → todo_manual.md           (blocked offers only)
```

Dedup, limits and the daily cap are exact set/count operations — an LLM re-reading the log to
compare URLs burns tokens *and* can miscompare.

## Editing the prompts

The markdown in `src/` is the program, and its token count is paid once per subagent. Two
rules, both learned the hard way:

- **Keep a line if removing it would change what the agent does; cut it if removing it would
  only change what the agent knows.** A warning the agent cannot act on is documentation — it
  belongs in this file, not in `src/`.
- **A bare prohibition names a symptom; the reason kills the cause.** "Don't read the log"
  blocks one filename, while the underlying impulse ("I should check for duplicates") simply
  routes around it. State the reason in one clause, then the rule — not a paragraph of
  architecture.

## Detail lives in `src/`, not here

The three "stop → manual" blockers, the anti-bot interaction model, the language rule, the
CV-variant mapping and the logging schema are specified in `src/applier_instructions.md` §7,
§6, §2, §5 and §9. Restating them here is how this file grew to 6 KB last time.
