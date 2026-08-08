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

Cowork mounts **exactly one folder**, and that mount is a hard filesystem boundary: the agent
cannot see, read, or write anything above it. So the runtime files live in `src/`, and
everything the agent has no business touching stays out of it.

```
claude_job_seracher/          <- never mounted; invisible to the agent
  CLAUDE.md  ARCHITECTURE.md  README.md
  finder/                     <- offer collection + triage + worklist (Python cockpit)
  docs/                       <- JUSTJOIN_API_NOTES.md and design notes
  legacy/                     <- frozen, superseded PowerShell pipeline
  trainer/                    <- prompt-optimization loop (its own Cowork mount)
  src/                        <- Cowork mounts THIS
    orchestrator_instructions.md   applier_instructions.md   profile.md
    portal_quirks.md   ats_quirks.md
    worklist.json  applications_log.jsonl  todo_manual.md  CV_PDF/
```

This replaces prose with geometry. The finder, its offer database and `CLAUDE.md` are all out
of reach, so nothing has to tell the orchestrator not to read them, and `CLAUDE.md` is not
injected into every subagent. **Keep it that way** — a file moved into `src/` is a file the
agent will find, and every extra token in there is paid once per subagent.

`portal_quirks.md` and `ats_quirks.md` are the pressure valve for that last rule. Per-form
recipes are long and each is needed on a minority of offers, so carrying them in the playbook
would charge every offer for them. Instead every offer ends up on **exactly one** kind of form —
the portal's own (justjoin modal, pracuj widget) or an external ATS — so the applier classifies
first and opens **one** of the two files. Anything true of one vendor's form and not of forms in
general belongs in one of them, not in the playbook. Keep them split for the same reason: merged,
a portal offer would pay for Workday recipes it will never use.

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

Two steps. Offer selection is a human review in the finder; applying is the agent.

```powershell
# 1. FINDER - harvest, score, pick. See finder/README.md.
python finder\app.py                 # open http://127.0.0.1:9000, hit "↻ Harvest" (both portals),
                                     # review, tick offers, "Write worklist"
```

Both portals land in one `offers_db.jsonl`; the same job on both collapses to one row carrying
both links, marked `jp` in the cockpit. The CLI harvesters (`harvest.py`, `harvest_pracuj.py`)
re-pull a single portal when one needs debugging.

The cockpit shows each offer's **applied** status (bot log + your manual marks), so you pick the
unapplied ones; **Write worklist** drops them into `src\worklist.json`. There is no daily cap —
how many you tick is the only throttle.

**2. PROSE** — open the **Claude desktop app (Cowork)**, connect the **`src/` folder** (not the
project root), and give it `orchestrator_instructions.md` as the task. It reads `worklist.json`
and spawns one fresh subagent per offer, each reading `applier_instructions.md` + `profile.md`
and driving one application.

- **It must run in Cowork, not the CLI.** Only Cowork's `claude-in-chrome` server can attach a
  CV (reads the file host-side → base64); the CLI forwards raw paths, which the extension
  rejects.
- `review` mode (default) = fill everything, **stop before final Submit**. `auto` = fill and
  submit.

## Data flow

```
finder/harvest.py + harvest_pracuj.py  →  finder/data/offers_db.jsonl   (every offer ever seen)
   → finder cockpit (app.py)  CODE: score + join applied-status; you pick
      → src/worklist.json
         → Cowork orchestrator  (trusts worklist, never re-filters)
            → one fresh subagent per offer  (applier_instructions.md + profile.md)
               → applies via Claude-in-Chrome, uploads CV
                  → applications_log.jsonl   (append-only audit trail)
                  → todo_manual.md           (blocked offers only)
```

`applications_log.jsonl` is the anti-double-apply record: the cockpit joins it back onto the
offer list so already-applied offers are visibly marked. The old set-based dedup lived in
`legacy/build_worklist.ps1` (frozen). The applier still must not read the log for dedup —
only to verify each outcome.

## Editing the prompts

The markdown in `src/` is the program, and its token count is paid once per subagent. The full
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
