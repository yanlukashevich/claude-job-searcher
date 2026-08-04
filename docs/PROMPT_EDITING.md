# How to change the prompts

Hand this to a new chat together with the change you want. It says what the files are, where a
change belongs, and how to word it. `CLAUDE.md` and `ARCHITECTURE.md` have the full design.

## What you are editing

The markdown under `src/` **is the program** — Claude Code is the runtime. There is no build and
no tests, so a wording change *is* a behavior change, and a sentence the agent can misread is a
bug. Every byte in `src/` is re-read **once per offer**, by a fresh subagent, so size is a real
cost — but never trade correctness for bytes.

## Where the change belongs

| Kind of change | File |
|---|---|
| A fact about Yan (experience, salary, links, CV paths, canonical answers) | `src/profile.md` |
| How the applier behaves (form filling, free-text, the loop, blocks, logging) | `src/applier_instructions.md` |
| A recipe for one portal's own form (justjoin modal, pracuj widget) | `src/portal_quirks.md` |
| A recipe for one external ATS vendor (eRecruiter, Workday…) | `src/ats_quirks.md` |
| How the queue is run (spawning subagents, verification, the report) | `src/orchestrator_instructions.md` |

Facts and behavior stay split: on a factual conflict `profile.md` wins, on behavior the playbook
wins. The two quirks files stay split too — each offer reads exactly one of them, so merging
would make a portal offer pay for Workday recipes it will never use. **Vendor-specific detail
belongs in a quirks file, never in the playbook.**

## How to word it

1. **Keep a line if removing it would change what the agent does; cut it if removing it would
   only change what the agent knows.** A warning it cannot act on is documentation — it belongs
   in `CLAUDE.md`, not in `src/`.
2. **Remove the cause, don't add a prohibition.** "Don't do X" blocks one symptom while the
   impulse behind it routes around the rule. Find the line that *produced* the behavior and
   delete or rewrite it. (Example: the applier copied pracuj's stiff boilerplate style — the fix
   was deleting "match the form's register", not adding "don't be formal".)
3. **State the reason in one clause, then the rule** — not a paragraph of architecture.
4. **Be concrete.** Name the actual button label, the actual field, the actual failure. Adjectives
   ("be polite, not too formal") drift; a one-line example sentence doesn't.
5. **Never invent hard facts.** Experience, salary, work authorization, certificates, dates: a
   required field with no fact behind it is a *block*, not a guess. Don't write a rule that lets
   the agent fill one in.

## How to work

- **Propose before editing.** Say what you'd change and why, in a few lines, and wait.
- **Smallest diff that does the job.** Don't restructure, rename, or move files as a side effect —
  a rename ripples into `CLAUDE.md`, `ARCHITECTURE.md` and the trainer, and is hard to review.
- **Don't touch `trainer/` or `legacy/`.** The trainer is a separate workflow with its own copies
  that are deliberately out of sync; `legacy/` is frozen.
- **Never edit `src/worklist.json` or `src/applications_log.jsonl`** — the finder writes one, the
  applier appends to the other.
- **After editing, check cross-references**: `§` numbers still point at the right sections, and
  every filename mentioned in `src/*.md` exists. Renumbering a section silently breaks pointers
  in the other files.
- **Report the byte delta** of `src/applier_instructions.md` — that is the per-offer cost.
