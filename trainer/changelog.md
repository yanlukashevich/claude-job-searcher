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

## Iteration 3 — 2026-07-13 (first iteration on the new free-text baseline)
Applier model: sonnet (all three runs)
Candidate size: 2189 words (prev: 2197 by `wc -w`; the 2120 in the out-of-band entry predates
later on-disk state — trust `wc -w`). Net −8 this iteration.
Offers (rotated off iter-2's Just Join IT offer):
- https://justjoin.it/job-offer/anitech-solutions-backend-developer-krakow-net — filled_review,
  external ATS **PeopleForce** (`anitechsolutions.peopleforce.io`, new vendor) — 2/2/2/2
  (54 actual calls vs self-reported ~35. Right CV dotnet/EN, salary 10000 PLN monthly gross
  unchanged, marketing consent + "where did you hear" left blank. Required consent checkbox
  ignored a ref-click → coordinate retry recovered it, iter-2 edit-2 recipe again. Mixed-language
  form handled by switching the page's own language `<select>` to English.)
- https://justjoin.it/job-offer/sii--net-developer-f-m-x--lodz-net — filled_review, custom
  homemade page (`sii.pl`) — 2/2/2/2 (39 actual vs ~28 reported. Polish form → Polish + PL CV;
  required LinkedIn resolved via the form's "Nie mam konta na LinkedIn" escape checkbox instead
  of inventing a URL or blocking; marketing consent + MySii account left off; disambiguated three
  near-identical forms on one page. The 4-years-C# requirement vs Yan's 2 handled as framing, not
  a block — correct.)
- https://justjoin.it/job-offer/future-processing-medium-net-developer-gliwice-net —
  blocked(dead-link), Apply handed off to `kariera.future-processing.pl` which 404s — 2/2/2/2
  (16 actual vs ~10 reported; §7.4 diagnosed on one get_page_text + one screenshot, cheapest
  possible run).
Recurring difficulties:
- No-op ref-click on a required control → coordinate retry: Anitech's consent checkbox, same
  pattern as iter-2 tomHRM's GDPR checkbox. The generalized recipe (iter-2 edit 2) fixed it
  again → CONFIRMED, no edit.
- justjoin Apply coordinate-click → new-tab handoff: all three runs, existing recipe worked.
- **Free-text policy went UNTESTED.** This iteration was meant to be the fresh baseline for the
  2026-07-13 required-only free-text rule, but no run hit a required free-text field: Anitech and
  Sii had no message/cover-letter field at all, Future Processing died before any form. The new §4
  behavior is therefore still unconfirmed by a live run — the reason the verdict is `continue`.
- Appliers still under-report their own tool-call counts (~35 vs 54, ~28 vs 39, ~10 vs 16);
  keep trusting harness numbers.
Noted but NOT edited (twice-rule — each is one occurrence):
- Mixed-language form (Anitech: Polish system labels + English recruiter-authored fields + a
  language switcher); §2 assumes one form language. Applier switched the whole form to English to
  match the English job description. If a second mixed-language form appears, §2 needs a clause on
  choosing when a switcher is present.
- Required field with an "I don't have one" escape checkbox (Sii LinkedIn). The field-mapping
  LinkedIn bullet's "only a required one is a problem" is imprecise — an escape checkbox resolves
  it without a block. If it recurs, tighten that bullet to "look for an escape checkbox before
  blocking."
- `read_page` truncating at ~10 elements below the fold (Anitech) → `find` per-field was the
  reliable fallback. One occurrence.
Edits (max 3):
  1. Consolidated the optional-free-text-blank rule that the 2026-07-13 out-of-band rewrite left
     stated three times (§4 + field-mapping intro + last field-mapping bullet): trimmed the intro's
     parenthetical and the last bullet's "Optional → blank, always" (−8 words) — hypothesis: pure
     token reduction; the rule still reads once in §4 and once as the field-mapping default, so no
     behavior change. Next iteration confirms scores didn't drop.
Reverted: none. iter-1 edit 1 (form_input→click+type) not re-triggered this iter — no silent
  form_input failure on a plain text input occurred. iter-2 edit 2 (no-op control → coordinate)
  confirmed again on Anitech. iter-2 edit 3 caused no greyed-submit misdiagnosis.
Proposed ats_quirks.md additions (for Yan, not applied):
- **PeopleForce** (`*.peopleforce.io`) — multi-employer ATS product, so it qualifies (Anitech
  reached it from justjoin via Apply → new tab). Recipes measured: compensation currency is a
  searchable custom listbox defaulting to **USD** — type "PLN", click the match; the page has a
  real language `<select>` (`form_input` works) — set it to match the CV/description language when
  field labels render mixed Polish/English; the required recruitment-consent checkbox ignored a
  ref-click and needed a coordinate-click fallback (the general no-op-control recipe already
  covers this — no need to name PeopleForce for it).
Proposed profile.md additions (for Yan, not applied): none — no missing-fact block this iteration.
Verdict: continue — all three runs at ceiling with no unresolved difficulty, but on the fresh
  free-text baseline that no run actually exercised. Not eligible for `done`: iter-2's 2/2/2/2s
  predate the free-text policy change and aren't comparable, so only one comparable iteration
  exists, and the new §4 rule is still unconfirmed. Next iteration should deliberately pick offers
  likely to present a **required** free-text field (eRecruiter "Informacje dodatkowe", a required
  cover letter/motivation) to confirm required-only composition and that optional messages stay
  blank, before any `done` call.

## Iteration 4 — 2026-07-13
Applier model: sonnet (all three runs)
Candidate size: 2186 words (prev: 2189 by `wc -w`). Net −3 this iteration.
Offers (rotated to fresh Polish corporates, chosen per iter-3's plan to try to surface a
**required** free-text field):
- https://justjoin.it/job-offer/lux-med-sp-z-o-o--programista-programistka-net-warszawa-net —
  filled_review, external ATS **eRecruiter** (`form.erecruiter.pl`) — 2/2/2/2 (39 harness calls
  vs self-reported ~25. Right CV dotnet/PL, Polish answers; salary band 10–15k PLN picked for the
  10000 gross figure; UoP employment; start "Natychmiast"; optional future-recruitment consent left
  blank. Clean coordinate-Apply → new-tab handoff; form_input rendered on all text fields, no
  fallback needed. No free-text field on the form.)
- https://justjoin.it/job-offer/pko-bp-finat-programista-net-programistka-net-warszawa-net —
  filled_review, external ATS **eRecruiter** (minimal 4-field variant) — 2/2/2/2 (28 harness vs
  ~20. Name/email/phone(E.164)/CV only; no salary/language/free-text fields at all. Clean run.)
- https://justjoin.it/job-offer/medicover--net-developer-warszawa-net —
  **blocked(missing-fact: hourly-netto B2B rate), mislabeled `filled_review` by the applier**,
  external ATS **eRecruiter** — 2/2/1/2 (33 harness vs ~25. Required radio "Stawka NETTO za godzinę
  pracy (B2B)" in zł/h bands; profile holds only a monthly-gross B2B figure, and §3.2 forbids
  altering salary, so the hourly-netto value is a genuine missing fact. C=2: correctly refused to
  invent it, right CV/language, English C1→"zaawansowany", C#/.NET "1-2 lata" not overstated.
  Co=2: everything fillable filled, optional GDPR consents blank. R=1: the loop says a required
  unknown hard fact → BLOCK and stop; the applier diagnosed the block perfectly but kept filling
  and reported outcome `filled_review` instead of `blocked(missing-fact)` — reasoned override, no
  thrashing, fully disclosed, but the playbook rule wasn't honored and the outcome was mislabeled.
  E=2: one large read_page on the Kraj/Region `<select>`s, self-corrected to `find`.)
Recurring difficulties:
- **Required free-text STILL untested — third iteration running.** All three offers routed to
  eRecruiter and NONE carried a message/motivation/cover-letter field. Across iters 2–4 (~8 runs)
  not one required free-text field has appeared. The required-only §4 rule remains unconfirmed by a
  live run; on this justjoin.it .NET pool it may simply not be exercisable (see verdict).
- **eRecruiter recipe over-specifies the form** — all three runs found the `ats_quirks.md` §6 recipe
  assumes a rich form (cookie wall, custom React listboxes, "Dodaj" language-row trap, banded
  salary), but the real instances were minimal or used genuine `<select>`s and had no cookie wall.
  The recipe should read as "handle if present," not "expect." → proposed ats_quirks.md note (Yan).
- **Mid-form missing-fact block vs review mode** — second+ occurrence of the "block found mid-form:
  stop or keep filling?" question (iter-1 Comarch, iter-2 edit 1 set "stop at once," now Medicover).
  The applier explicitly called the "staged fields don't survive the tab" rationale false in review
  mode (the user keeps the tab), kept filling, and mislabeled the outcome. → edit 1.
- Appliers still under-report their own tool-call counts (~25 vs 39, ~20 vs 28, ~25 vs 33); keep
  trusting harness numbers.
Noted but NOT edited (twice-rule — first occurrence):
- **Hourly-rate salary field with no hourly figure in profile** (Medicover B2B zł/h netto bands).
  Profile's "give the B2B figure unchanged even if labeled netto" note covers a *monthly-netto*
  rewording, not a *period* change (hourly). First occurrence → routed to a profile.md proposal for
  Yan rather than a candidate rule. Edit 1 already clarifies the block/outcome behavior generally.
Edits (max 3):
  1. Loop's missing-fact block line rewritten: dropped the auto-only rationale ("staged fields don't
     survive the tab, so finishing is waste") that misled the review-mode run; now scopes by mode
     ("Auto: stop now. Review: fill the rest for the user, still report it blocked") — hypothesis:
     removes the mid-form-block/review-mode contradiction and stops missing-fact blocks being
     mislabeled `filled_review` (Medicover). Net −3 words.
Reverted: none. iter-2 edit 1 ("stop filling at once") is *superseded* by this edit's mode-scoping,
  not reverted — its "no hesitation" goal held for early blocks but broke on a genuine mid-form block
  in review mode. iter-1 edit 1 (form_input→click+type) not re-triggered (no silent form_input
  failure this iter). iter-2 edit 2 (no-op control → coordinate) not triggered (clean ref-clicks
  throughout). No greyed-submit misdiagnosis.
Proposed ats_quirks.md additions (for Yan, not applied):
- **eRecruiter** (`form.erecruiter.pl`): reframe §6 as *conditional*. Instances vary enormously by
  employer template — several this iteration had no cookie wall, real `<select>`s (not custom
  listboxes), no language section / "Dodaj" trap, and no message field. Recipe steps should be
  "handle if present," not "expect." Also: §6's "fill the message field with form_input" now
  *contradicts* the candidate's post-2026-07-13 required-only §4 — when the eRecruiter message field
  ("Informacje dodatkowe"/"Dodatkowe uwagi") is optional, it must stay blank. That §6 line should be
  scoped to "only if required." (Not triggered this run — no instance showed the field — but it is a
  live contradiction waiting to fire.)
Proposed profile.md additions (for Yan, not applied):
- **Hourly rate, B2B (netto, zł/h)** — OBSERVED once (Medicover eRecruiter required a radio
  "Stawka NETTO za godzinę pracy (B2B)" with bands 100–120 / 120–140 / 140–160 / 160–180 / >180
  zł/h netto; profile holds only monthly gross, and §3.2 forbids converting). Shape: a PLN/hour
  *netto* figure or band, distinct from the monthly bands already in `Employment`. Likely to recur
  on B2B-oriented forms that price by the hour. Never guess the value — only Yan knows it.
Verdict: continue. Not `done`: Medicover is 2/2/1/2 (below the 2/2/2 gate), and the required-only
  §4 free-text rule is *still* unexercised after three iterations — no unresolved-difficulty-free
  ceiling pair exists. Not `plateau`: the candidate shrank (−3) and edit 1 addresses a live
  contradiction. **Guidance for Yan / next iteration:** the justjoin.it .NET pool routes almost
  everything to eRecruiter or minimal internal forms, none of which have surfaced a required
  free-text field in ~8 runs — confirming required-only §4 against this pool may be infeasible.
  Either (a) accept §4 as conservative-but-untested and stop gating `done` on it, or (b) add a test
  offer known to demand a cover letter / motivation (e.g. a SmartRecruiters or Workday posting with
  a required letter). Next iteration should also re-run one B2B-hourly offer to confirm edit 1 makes
  the applier emit `blocked(missing-fact)` rather than `filled_review`.

## Iteration 5 — 2026-07-13
Applier model: sonnet (all three runs)
Candidate size: 2178 words (prev: 2186 by `wc -w`). Net −8 this iteration.
Offers (Medicover rerun to confirm iter-4 edit 1; two fresh vendors per iter-4's plan to
surface a required free-text field):
- https://justjoin.it/job-offer/medicover--net-developer-warszawa-net (rerun, targets iter-4
  edit 1) — blocked(missing-fact: hourly-netto B2B rate), external ATS **eRecruiter** — 2/2/2/2
  (~47 harness calls vs self-reported ~30. **iter-4 edit 1 CONFIRMED**: this time the applier
  emitted `blocked(missing-fact)`, not `filled_review` — the mode-scoped block line worked as
  designed, filled the rest for the user and still reported blocked. Right CV dotnet/PL, English
  C1→"C1 - zaawansowany", experience "1-2 lata" not overstated, optional consents blank. Only
  waste: two 6700-char `read_page` dumps of the 170-country `<select>` — self-flagged, `find`
  would have been cheaper.)
- https://justjoin.it/job-offer/motorola-solutions-junior-c-engineer-krakow-net —
  blocked(register), external ATS **Workday** (`*.wd5.myworkdayjobs.com`) — 2/2/2/2 (~23 harness
  vs ~14. All three entry paths ("Apply Manually" / "Autofill with Resume" / "Use My Last
  Application") converge on a mandatory step-1-of-7 "Create Account/Sign In"; correctly refused to
  type credentials and blocked on sight, didn't waste calls re-testing the other two paths.
  Confirms iter-1's proposed Workday register-block-on-sight.)
- https://justjoin.it/job-offer/vercom-s-a--ai-first-backend-software-engineer-poznan-net-3ee02de7 —
  blocked(missing-fact: monthly-netto B2B salary) — **WRONG block**, external ATS **Traffit**
  (`*.traffit.com`, new vendor) — **1/1/2/2** (~54 harness vs ~40. **§4 required-only free-text
  FINALLY exercised and CONFIRMED**: a required (`*`) "Z jakich narzędzi AI korzystasz
  najczęściej?" field got a composed 1–2 sentence note grounded in profile ("LLM integration into
  applications"), verbatim: *"Na co dzień integruję modele LLM (wywołania API) w budowanych
  aplikacjach, a przy pisaniu i refaktoryzacji kodu korzystam z asystentów AI jako stałego
  elementu swojego workflow."* — while the optional "Chcesz nam coś więcej o sobie powiedzieć?"
  narrative was correctly left blank. **C=1, Co=1**: it blocked the required "oczekiwania
  finansowe netto (B2B)" field as a missing fact, but `profile.md` §Employment **explicitly**
  answers it — "A form asking B2B *netto per month* gets this figure unchanged" (8000–10000 /
  10000). The applier over-applied §3-rule-2 (no-convert) to a case needing no conversion, and
  left a fillable required field blank → edit 1. R=2: consent checkbox ignored a ref-click →
  coordinate retry recovered it (existing recipe), custom listboxes + city autocomplete handled
  without flailing. E=2.)
Recurring difficulties:
- **B2B salary netto/gross handling** — Medicover (hourly netto → CORRECT block) and Vercom
  (monthly netto → WRONG block). The applier can't reliably tell the profile's two adjacent
  netto cases apart: monthly-netto = fill unchanged, per-hour-netto = block. Form-general (Polish
  B2B forms routinely say "netto") and it caused the only real quality failure this iteration →
  edit 1.
- justjoin Apply coordinate-click → new-tab handoff: all three runs, existing recipe worked.
- Appliers still under-report their own tool-call counts (~30 vs 47, ~14 vs 23, ~40 vs 54);
  keep trusting harness numbers.
Noted but NOT edited:
- **Optional identity/link fields: fill or blank?** (Vercom flagged) — §6 field-mapping intro
  ("Default for every optional field: leave it blank") **contradicts** the LinkedIn/GitHub bullet
  ("If LinkedIn is missing and the field is optional, skip it" — implying: fill it when present).
  Vercom filled optional phone/LinkedIn/GitHub as low-risk identity facts and flagged the tension.
  Resolving this changes what "correct" *means* (the scoring rubric currently reads "every optional
  field left blank"), so it is a **policy call for Yan, not a trainer edit** — routed below. Left
  as-is this iteration; the applier's reading was reasonable and did no harm.
- **§7 stop-triggers vs the loop's "Review: fill the rest" clause** (Motorola flagged) — the
  loop line "Review: fill the rest for the user, still report it blocked" is scoped to missing-fact,
  but reads as *maybe* applying to register/captcha/dead-link too. Applier resolved it correctly
  (register = unconditional stop, nothing to fill). First occurrence → note only.
- **`read_page` on a long `<select>` dumps every option** (Medicover country list, 6700 chars ×2)
  — wasteful vs `find`/`form_input`. First occurrence → note; add a rule if it recurs.
Edits (max 3):
  1. Salary field-mapping bullet rewritten to cover the netto label: period-unspecified **or
     netto-labelled monthly** → give the profile figure unchanged (never convert netto↔gross);
     only a **per-hour** rate is a missing fact — hypothesis: removes Vercom's wrong monthly-netto
     block; next iteration re-runs a monthly-netto B2B offer and expects a filled salary, not a
     block. (+~5 words.)
  2. Cut "; never go hunting for an optional field to put a note in" from the message field-mapping
     bullet — the same rule is already stated in §4 and in the field-mapping intro (thrice total);
     token reduction, no behavior change. (−~11 words.)
Reverted: none. **iter-4 edit 1 (mode-scoped missing-fact block) CONFIRMED** on Medicover — the
  exact rerun it was written for now reports `blocked(missing-fact)` instead of `filled_review`.
  iter-1 edit 1 (form_input→click+type) not re-triggered (no silent form_input failure). iter-2
  edit 2 (no-op control → coordinate) confirmed again on Vercom's consent checkbox. No greyed-submit
  misdiagnosis.
Proposed ats_quirks.md additions (for Yan, not applied):
- **Traffit** (`*.traffit.com`) — multi-employer ATS product, qualifies (Vercom reached it from
  justjoin via Apply → new tab). Recipes measured: dropdowns are custom React listboxes (open by
  `ref`, `find` options, click by `ref`); Kraj prefilled "Polska"; Miasto is a type-ahead
  autocomplete (type city, pick the matching option); a required consent checkbox's first ref-click
  only expanded its "Pokaż więcej" text → coordinate-click the checkbox square (general no-op recipe
  already covers this). No cookie wall, no hidden file input this instance.
- **Workday** (`*.myworkdayjobs.com`) — re-affirming iter-1's proposal: every entry path ends at a
  mandatory "Create Account/Sign In" step 1; no guest path → register-block on sight. (Motorola
  confirmed again; still absent from `ats_quirks.md`.)
Proposed profile.md additions (for Yan, not applied):
- Standing item still open: **Hourly rate, B2B (netto, zł/h)** — Medicover blocked on it again this
  iteration (`(brak — do uzupełnienia)` in profile). Value still needed; never guess. (No *new*
  missing-fact this iteration — Vercom's monthly-netto ask was answerable and is now handled by
  edit 1, not a profile gap.)
Proposed policy decision (for Yan): resolve the optional-identity-field contradiction above. Either
  (a) optional phone/LinkedIn/GitHub from the profile should be **filled** (product-sensible; then
  the §6 intro's "every optional field → blank" must be narrowed to free-text/narrative + optional
  consents, and the rubric's "every optional field left blank" reworded), or (b) they stay **blank**
  (then the LinkedIn/GitHub bullet must drop its "only a required one is a problem" implication).
  The candidate can't be made internally consistent without picking one.
Verdict: continue. Not `done`: Vercom is 1/1/2/2 (below the 2/2/2/≥1 gate) due to the wrong
  salary block, so no unresolved-difficulty-free ceiling pair exists. **Milestone reached though:**
  the required-only §4 free-text rule is finally confirmed by a live required field (Vercom AI-tools
  question composed correctly, optional narrative left blank) — the gap that blocked `done` in iters
  3–4 is closed. Not `plateau`: candidate shrank (−8) and edit 1 fixes a real failure with a testable
  hypothesis. **Next iteration:** re-run a monthly-netto B2B offer (e.g. rerun Vercom) to confirm
  edit 1 makes the applier *fill* the salary rather than block; a clean 2/2/2/2 there plus one more
  ceiling iteration would put the candidate in reach of `done`.
