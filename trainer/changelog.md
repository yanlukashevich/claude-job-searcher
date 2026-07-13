# Trainer changelog

One entry per iteration, newest at the bottom. This file is the trainer's memory across
sessions — read it before doing anything.

Entry template:

```
## Iteration N — YYYY-MM-DD
Applier model: <sonnet — flag it loudly if anything else ran>
Candidate size: <wc -w> words (prev: <n>)
Offers: <url — outcome — scores C/Co/R/E> (one line each)
Recurring difficulties: <what showed up more than once, or "none">
Edits (max 3):
  1. <one-line diff summary> — hypothesis: <what failure this removes>
Reverted: <edits from iteration N-1 whose hypothesis failed, or "none">
Proposed ats_quirks.md additions (for Yan, not applied): <popular ATS products + general
  traps only — never one employer's homemade page; or "none">
Proposed profile.md additions (for Yan, not applied): <every missing-fact block: the field,
  the form that demanded it, the value's shape, whether it recurs; never guess the value —
  or "none">
Verdict: continue | done | plateau
```

---

## Iteration 0 — 2026-07-11 (baseline)
Candidate size: 2252 words
`candidate_applier.md` is a verbatim copy of the production playbook
(`applier_instructions.md`) as of 2026-07-11. No runs yet, no scores.
Verdict: continue

## Iteration 1 — 2026-07-11
Applier model: sonnet (all three runs)
Candidate size: 2330 words (prev: 2252 — but measured differently; by today's `wc -w`
the pre-edit file was 2343, so this iteration is net −13. Use `wc -w` from now on.)
Offers:
- https://justjoin.it/job-offer/skywise-junior-net-backend-developer-gdansk-net — blocked(register), Workday account wall — 2/2/2/2 (~14 calls; clean diagnosis of no-op Apply click)
- https://justjoin.it/job-offer/comarch--net-developer-krakow-net-fe2872fc — blocked(missing-fact: date of birth), custom ATS kariera.comarch.pl — 2/1/2/1 (Co: filled optional salary/employment-form/GitHub against blank-default, citing the field-mapping bullets as authority; E: 105 actual tool calls — self-reported "~55", per-field screenshot loop after form_input silently failed)
- https://justjoin.it/job-offer/mettler-toledo-fullstack-software-engineer-all-genders--warszawa-net — filled_review, external ATS Avature (careers.mt.com) — 2/1/1/1 (Co: English+Russian language rows never added, "Native" select unverified; R: stray Enter advanced the wizard past two steps, not recovered; E: 171 actual tool calls — self-reported "~90")
Recurring difficulties:
- justjoin Apply ref-click no-op → coordinate-click retry: hit in ALL THREE runs; the
  playbook's existing recipe resolved it each time at ~2 extra calls. No edit needed.
- `form_input` silently failing on plain text inputs (value never renders): runs 2 AND 3,
  both times triggering an expensive per-field screenshot-verification loop. → edit 1.
- Appliers under-report their own tool-call counts by ~2x (55 vs 105, 90 vs 171). Trust
  the harness usage numbers, not §6 of the report.
Edits (max 3):
  1. §6 "never trust success" bullet rewritten: form_input-first, but after its FIRST silent
     failure on a form switch to click+type for all remaining text fields, and verify one
     screenshot per section instead of per field — hypothesis: removes the per-field
     verification loop that dominated cost in runs 2 and 3.
  2. Field-mapping default line now states the bullets map a value's *source* when a field
     must be filled and never make an optional field worth filling — hypothesis: removes
     run 2's "bullets vs blank-default" contradiction (it volunteered salary unprompted,
     which can also hurt the application).
  3. Cut the "greyed-out Submit is usually styling" bullet (−34 words) — unused in all
     three runs; token reduction. Restore if a greyed-submit misdiagnosis ever appears.
Noted but NOT edited (twice-rule): run 2 asked whether a §7 block discovered mid-form
should stop filling immediately (staged fields don't survive the tab, so filling the rest
is waste in auto mode). One occurrence = anecdote; edit next time it appears.
Reverted: none (first iteration).
Proposed ats_quirks.md additions (for Yan, not applied):
- Workday (`*.myworkdayjobs.com`): both "Apply Manually" and "Autofill with Resume" end at
  a mandatory create-account step; no guest path → treat as register-block on sight.
- Comarch (`kariera.comarch.pl`): hidden `display:none` file input (unhide via JS, upload
  by ref, dispatch input/change); free-text and salary fields reject the "/" character and
  the validation message stays stale until an unrelated field is blurred; requires date of
  birth (missing-fact block for Yan's profile — every Comarch offer will block on this).
- Avature (`careers.mt.com`): must click the visible "Z urządzenia" method button or the
  Continue button stays hidden after file_upload; `type="month"` inputs need month-segment
  click + Right arrow before the year; country field in repeating rows is a searchable
  combobox; accessibility tree is unreliable for repeating-row widgets — trust screenshots;
  a stray Enter advances the whole wizard.
- Generalize the Symfonia iframe-file-input recipe to "hidden/off-DOM file input".
Verdict: continue

## Iteration 2 — 2026-07-11
Applier model: sonnet (both runs)
Candidate size: 2327 words (prev: 2330)
Offers:
- https://justjoin.it/job-offer/comarch--net-developer-krakow-net-fe2872fc (rerun, targets iter-1 edits 1+2) — blocked(missing-fact: date of birth), custom ATS kariera.comarch.pl — 2/2/2/2 (55 actual calls vs 105 in iter 1 on the same offer; after form_input's first silent failure it switched to click+type with no per-field screenshot loop → edit 1 hypothesis CONFIRMED; no optional fields volunteered → edit 2 consistent, though the early block limits the evidence; ~9 calls lost to transient tabs_context_mcp infra errors, not playbook's fault)
- https://justjoin.it/job-offer/just-join-it-fullstack-software-engineer-remote--gdansk-net-0bbc17e3 — filled_review, external ATS tomHRM (tomhrm.app, new vendor) — 2/2/2/2 (46 actual calls; three stalls — Apply ref-click no-op, GDPR checkbox ref-click no-op, Dropzone hidden file input on <body> — all self-diagnosed and recovered; correctly left optional fields and marketing consent blank; no message field existed so nothing composed)
Recurring difficulties:
- "Block found mid-form: keep filling or stop?" ambiguity — second occurrence (iter 1
  Comarch + this Comarch rerun); twice-rule satisfied → edit 1.
- Silent no-op ref-clicks are not Apply-specific: tomHRM's required GDPR checkbox ignored
  a ref-click and needed the same coordinate-click retry → edit 2 (generalizes the
  existing recipe rather than adding a rule).
- Hidden/off-DOM file inputs: second vendor in two iterations (Comarch display:none,
  tomHRM Dropzone on <body>) — confirms iter 1's proposed ats_quirks.md generalization.
- Appliers still under-report their own tool-call counts (~35 vs 55, ~30 vs 46); keep
  trusting harness numbers.
Noted but NOT edited (twice-rule): tomHRM asks the same expected salary as netto (B2B)
and brutto (zlecenie) Od–Do rows; applier repeated the single profile figure in all four
cells and flagged it. One occurrence = anecdote; if a second dual-basis salary form
appears, add a mapping rule.
Edits (max 3):
  1. Loop's BLOCK line now says stop filling at once (staged fields don't survive the
     tab) — hypothesis: removes the recurring mid-form-block hesitation and the wasted
     fill calls after a confirmed blocker.
  2. Apply-diagnosis no-op bullet generalized to any control that visibly ignores a
     ref-click (checkboxes included); cut the redundant "one time re-reading the tab list"
     sentence — hypothesis: removes troubleshooting cost on non-Apply no-op clicks (4
     calls on tomHRM's checkbox).
  3. Cut the parenthetical previewing ats_quirks.md's contents (knowledge-only,
     duplicates that file) — token reduction.
Reverted: none — iter-1 edit 1 confirmed; edit 2 weakly confirmed (early block); edit 3
caused no greyed-submit misdiagnosis.
Proposed ats_quirks.md additions (for Yan, not applied):
- tomHRM (`tomhrm.app`): required checkboxes may ignore ref-clicks → coordinate-click
  fallback; CV input is a Dropzone hidden input attached to <body> → tag it with a temp
  id via JS, then find + file_upload (Dropzone auto-processes); salary is dual-basis
  Od–Do rows (B2B netto + zlecenie brutto).
- Re-proposing from iter 1: retitle the Symfonia iframe recipe to "hidden/off-DOM file
  input" — now seen on three vendors (Symfonia, Comarch, tomHRM).
Verdict: continue

## Out-of-band change — 2026-07-13 (Yan, by hand — not an iteration, no runs, no scores)
Candidate size: 2120 words (prev: 2141 as measured on disk immediately before this change; the
2327 recorded in iter 2 predates later hand-edits — trust `wc -w`, not the previous entry).

Three policy changes, none of them driven by a run. They change what "correct" *means*, so
scores before and after this line are not comparable — the next iteration is a fresh
baseline for free-text behavior.

1. **Free text is now required-only.** §4 rewritten: every free-text field (employer message,
   "introduce yourself", motivation, cover letter, open questions) stays blank **unless the
   form cannot be submitted without it**. The old "one exception: always write the employer
   message" rule is gone, and with it the field-mapping bullet that told the applier to hunt
   for an "Informacje dodatkowe" field to put a note in. The note rules (1–2 sentences, hooked
   to the offer, no invented tech) now apply only when a field is required. The scoring rubric
   moved with it: a volunteered optional message is now a **Completeness miss**, not a bonus.
2. **`ats_quirks.md` is for popular ATS products only.** A section is earned by a vendor many
   employers use (eRecruiter, Workday, Avature, Greenhouse, tomHRM …) or by a trap any form can
   spring — never by one company's homemade career page, whose recipe every applier would pay
   for on every external offer and use on one. The Symfonia iframe recipe was accordingly
   generalized (as iters 1 and 2 both proposed) into **General traps → hidden/off-DOM file
   input**, covering the `display:none`, iframe and Dropzone-on-`<body>` variants, with no
   company named.
3. **Missing facts now have a channel.** `missing-fact` blocks used to be dead ends. The
   changelog template and `trainer_instructions.md` §5 now require a *proposed `profile.md`
   addition* for each one: the field, the form that demanded it, the value's shape, whether it
   recurs. The trainer never edits `profile.md` and never guesses a value.

profile.md additions — **proposed, then filled by Yan the same day** (values are his; the
trainer never guesses one). `profile.md` now carries:
- **Date of birth** = 15.07.2000 (`Personal`) — OBSERVED, twice: `kariera.comarch.pl` requires
  it and blocked iters 1 and 2 on the same offer. That `missing-fact` block should now be gone;
  the iter-2 Comarch offer is worth one rerun to confirm it.
- **Citizenship** = białoruskie (`Personal`) — ANTICIPATED: Workday-class forms ask citizenship
  and residence as separate required fields; the profile only had residence. Consistent with the
  existing Work-authorization section (karta stałego pobytu, no sponsorship needed).
- **Salary bands** (`Employment`) — OBSERVED once (tomHRM asked B2B and UoP/zlecenie as separate
  Od–Do rows; the applier repeated the lone 10000 figure into all four cells and flagged it).
  Now Od–Do = 8000–10000 PLN on both bases, **both gross** — the same band on B2B and UoP is
  deliberate, and the file says so, so a future run can't "fix" it by converting netto↔brutto.
- **Total years of commercial experience** = 3 (`Experience`) — ANTICIPATED: a common single
  required number the applier would otherwise have to derive from the per-tech table (§3 forbids
  inventing it).
- **Education end** = 07.2026 (`Education`) — ANTICIPATED: wizard ATS (Workday, Avature) demand
  month + year, and the entry carried only "2022 – 2026".
