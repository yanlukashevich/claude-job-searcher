# Auto Job Applier — Architecture

A tool that applies to jobs on your behalf using your prepared CV, by driving your
real Chrome browser. Starts with **justjoin.it**, later extends to **pracuj.pl**.

Status: **Phase 1 running** — the Applier drives real applications in review mode and the
Finder (`finder/`) is built. This document is the source of truth for the design.

---

## 1. Goal

Given job offers on justjoin.it, apply to them automatically — including the many
offers that redirect to external ATS systems or custom company sites where forms
must be filled in. The tool should **drive each application to completion**, compose
answers to unusual questions itself, and only fall back to manual for a small set of
genuinely blocked cases.

---

## 2. Engine

**Claude-in-Chrome (MCP)** drives the user's real, logged-in Chrome.

Why not a pure Playwright/Puppeteer script: scripted selectors are brittle and cannot
*reason about* an external form they have never seen. The whole point is handling
arbitrary, unpredictable forms, which requires live reasoning per page.

The user is **logged into justjoin.it** in this Chrome profile.

---

## 3. Two tools, shared data

The system is split into two independent tools so the offer-collection step and the
apply step can be run and reviewed separately.

### 3.1 Finder — BUILT (`finder/`, Python, see `finder/README.md`)
- **Input:** search criteria (stack, seniority) baked into `harvest.py`'s API query.
- **Job:** pull justjoin.it's JSON listings API (confirmed to exist; recon paid off) into an
  offer DB that only ever grows — an offer that leaves the feed is marked `archived_at`
  (expired) rather than deleted — score every offer with a keyword classifier, and serve a
  local **cockpit** (`app.py`) where the user reviews and picks (expired hidden by default).
- **Dedup:** the cockpit joins `applications_log.jsonl` (bot) and `manual_applied.json` (you)
  onto each offer as a visible **applied** status, so already-applied offers are skipped by
  the human at pick time — no automatic set-filter (that was `legacy/build_worklist.ps1`).
- **Output:** `src/worklist.json` — written straight from the cockpit's picks.

### 3.2 Applier
- **Input:** `worklist.json` + `profile.md` + `applier_instructions.md` + CV file(s).
- **Job:** fully autonomous across **all** apply variants:
  - internal justjoin.it apply modal,
  - external ATS (Greenhouse / Lever / Workable / SmartRecruiters / …),
  - custom company sites.
- Fills forms, composes answers to free-text / unusual questions, drives each to
  completion, and logs every outcome.

---

## 4. Data files

| File | Purpose |
|------|---------|
| `profile.md` | **The facts** — source of truth for all factual answers. |
| `applier_instructions.md` | **The behavior** — how Claude fills forms and composes answers. |
| `cv/` | The CV file(s), possibly variants per stack. |
| `applications_log.jsonl` | Audit trail of every outcome; also the anti-double-apply record. |
| `finder/data/offers_db.jsonl` | Every offer ever harvested; the finder's source of truth. |
| `worklist.json` | Finder cockpit output; applier input (the offers picked for this batch). |
| `todo_manual.md` | Offers the tool could not finish, with URL + reason, for manual handling. |

### 4.1 `profile.md` (facts only)
Personal details, contacts, links (LinkedIn/GitHub/portfolio), CV path, experience,
canned answers to recurring questions: expected salary, notice period, work
authorization, relocation, years per technology, "why me" material.

### 4.2 `applier_instructions.md` (behavior / operating manual)
Kept separate from data so tone/rules can change without touching facts.
Sections:
- **Role & goal** — fill applications on behalf of the user; `profile.md` is the
  sole source of truth for facts.
- **Language rule** — answer each field in the **language of the form** (Polish form →
  Polish answers, English form → English); match its register.
- **Hard rules** — never invent facts not in `profile.md` (experience, salary, work
  auth, certs, dates); never alter salary / notice period / work-auth values; one
  consistent identity everywhere.
- **Free-text style** — cover-letter / "why us" fields composed from profile + job
  description; concise, honest, first person, no cliché buzzwords; tone guide.
- **Field-mapping guidance** — how to match common fields and defaults for optional ones.
- **Logging & stop policy** — see below.

---

## 5. Applier behavior

### 5.1 Outcomes (keeps going, logs everything)
1. **Applied cleanly** — every field matched the profile directly.
2. **Applied with reasoning** — a free-text / unusual question was *composed*. The exact
   text written is logged so the user can audit what went out in their name.
3. **Blocked → `todo_manual.md`** — only the cases in 5.2.

The log is an **audit trail**, not a stop-list. The tool keeps applying in all cases
except a genuine block.

### 5.2 The only "stop and go to manual" triggers
1. **CAPTCHA / bot-detection / "I'm not a robot".** Handed to the user — the tool does
   not attempt to defeat anti-bot systems.
2. **Forced account registration.** If a site requires creating an account, log to
   `todo_manual.md` and skip. (No auto-registration; Gmail is **not** accessed.)
3. **Missing required hard-fact.** A required field whose answer is not in `profile.md`
   and cannot be safely invented (e.g. a specific certification number).

### 5.3 Safety rules
- **Never fabricate hard facts** — experience, salary, work authorization, certs, dates
  come only from `profile.md`. Missing → blocked, never guessed.
- **Free-text is fair game** — composed from profile + job description, always logged
  verbatim.

### 5.4 Submit policy
- Build a **review mode** and an **auto-submit mode**, switched by a config flag.
- **Phase 1: review mode** (fill, then stop for user to submit) to build trust.
- Flip to **auto-submit** once proven.

---

## 5A. How the Applier runs (components + loop)

The Applier is not a compiled program — it is an **agentic loop**: a Claude-in-Chrome
session that reads the playbook (`applier_instructions.md`) + facts (`profile.md`)
and drives the browser one offer at a time.

```
open offer URL
 → click "Apply"  (may open modal, redirect, or open a new tab)
 → detect apply-type: internal modal | external ATS | custom | register-required | captcha
 → read the form (structured text, not pixels)
 → map each field → profile value | compose free-text | mark unknown
 → fill fields + upload CV
 → blocked? (captcha / forced register / missing hard-fact) → log to todo_manual, next
 → submit (review-mode: stop) OR (auto-mode: click)
 → verify success (confirmation text / URL change)
 → write outcome to applications_log.jsonl
 → next offer
```

Components:

| # | Component | Responsibility | Main tools |
|---|-----------|----------------|-----------|
| 0 | Finder cockpit | harvest, score, join applied-status, human picks → `worklist.json` | `finder/` (Python, §5C) |
| 1 | Orchestrator | read `worklist.json`, spawn one subagent per offer, pace, verify logs | Cowork parent agent (§5C) |
| 2 | Navigator | open offer, click Apply, follow redirects/new tabs | `navigate`, `tabs_*`, `find` |
| 3 | Apply-type detector | classify page into one of 5 types | `get_page_text`, `find` |
| 4 | State reader | extract current form structure/fields | `get_page_text`, `read_page` |
| 5 | Field mapper | form field → `profile.md` value; flag unknowns | reasoning |
| 6 | Answer composer | free-text from profile + job desc, in form's language | reasoning |
| 7 | Form filler | type values, select options, upload CV | `find`→`computer` (`ref`), `form_input`, `file_upload` |
| 8 | Blocker detector | captcha / register-wall / missing-fact → route out | `get_page_text`, `find` |
| 9 | Submitter | review-mode stop, or auto-submit click | `find` → `computer left_click ref=…` (see 5B) |
| 10 | Verifier | confirm submission went through | `get_page_text` |
| 11 | Logger | append `applications_log.jsonl` + `todo_manual.md` | file writes |

"Building" these means producing: the **playbook**, the **data schemas**, and a few
**reusable JS snippets** (dump all form fields as JSON, detect captcha nodes) run via
`javascript_tool`.

---

## 5B. Browser interaction variants — MEASURED (2026-07)

The core anti-bot tell is `event.isTrusted`: browser-generated input is `true`
(indistinguishable from a human), JS-synthesized input is `false` (flaggable). We
**measured** how claude-in-chrome's tools behave on the real logged-in Chrome instead
of guessing:

| Method | click `isTrusted` | typing `isTrusted` | events fired |
|--------|-------------------|--------------------|--------------|
| **`computer`, `coordinate=[x,y]`** | **true** | **true** (per-char keydown+input) | full chain (below); real keystrokes |
| **`computer`, `ref=ref_N`** | **true** | n/a — `type` has no `ref` | **identical full chain** + auto-scrolls element into view first |
| **`form_input`** (DOM) | sets value directly | **false** | only synthetic input+change; no focus/keystrokes |
| raw JS `.click()` | **false** | — | synthetic only |
| **read** (`get_page_text`/`find`/`read_page`) | — | — | **no events at all — zero footprint** |

The full chain, identical for both `computer` click variants:
`mouseover → mouseenter → pointerdown → mousedown → focus → mousemove → pointerup →
mouseup → click` (`detail=1`), every event `isTrusted=true`.

**Conclusion (evidence-backed):**
- The **vision tool is genuinely more anti-bot-resistant** — its actions are dispatched
  at Chrome's real input layer (CDP), so `isTrusted=true` with a natural event chain.
- **`ref` is resolved to the element's bounding-box center and then dispatched through the
  exact same CDP path as a coordinate** — there is no `element.click()` fallback. It is
  *equally stealthy and strictly more robust*: measured against a button 3067px below a
  674px viewport, the ref click **scrolled the page (scrollY 0 → 2524) and then clicked at
  a real, visible coordinate**. A blind coordinate click would have hit whatever happened
  to be at those pixels. justjoin.it's Apply/Submit buttons are frequently below the fold.
- **`form_input` works but is detectable** (`isTrusted=false`) — fine for low-sensitivity
  fields, not for guarded ones.
- **Reading is free and invisible** regardless of method.

**Strategy — perceive cheap, act careful:**
1. **Always perceive with cheap text tools** (`get_page_text`/`find`) — no anti-bot cost,
   low tokens. Never spend screenshots just to read.
2. **Use the vision `computer` tool for the sensitive actions** — clicking **Apply**,
   clicking **Submit**, and typing on any reCAPTCHA-guarded page — with deliberate
   human-like delays. These are the moments reCAPTCHA v3 scrutinizes most.
   **Prefer `ref` over `coordinate`:** `find` (cheap text, invisible) → `computer
   left_click ref=…` gives a trusted click for **zero image tokens**. Screenshots are then
   only for diagnosing a confusing page, never for routine clicking.
   - **Refs die on navigation.** Re-`find` after every navigate / modal-open / redirect;
     a stale ref errors with *"No element found with reference"*. Never cache refs across
     pages.
   - **`type` takes no `ref`** — it types into the *focused* element. Pattern:
     `left_click ref=…` (focuses it) → `type`. Still screenshot-free.
   - `hover` and `scroll_to` also accept `ref`.
3. **`form_input` is acceptable for low-sensitivity fields** (speed/tokens), treated as
   "works, not stealthy."
4. **Batch** independent actions via `browser_batch` to cut round-trips/tokens.
5. The big protections are already free: **real IP, genuine Chrome fingerprint, warm
   logged-in session.** Remaining risk is behavioral — pace like a human, don't
   machine-gun applications.
   - **The real mouse tell:** the cursor does not fail to move — it **teleports**. Both
     click variants fire exactly **one** `mousemove`, landing on the target; a human emits
     dozens en route. (An earlier note here claimed "no mouse-movement telemetry" — that
     was wrong; `mouseover`/`mouseenter`/`mousemove` all fire, trusted.) Later refinement:
     a `computer hover` (also `ref`-capable) on a nearby element before the sensitive click
     buys a second, distinct movement.

Anti-bot context: three overlapping watchers — (1) Cloudflare edge (per-request,
cross-site reputation, issues `cf_clearance`), (2) justjoin.it's own account-abuse logic
(**this is what bans your account** — accumulated behavior over time), (3) embedded
Google reCAPTCHA v3 (invisible cross-site score tied to your Google identity; a challenge
appears on low score or sensitive actions like Submit). Pacing on a warm session is the
main protection against (2).

---

## 5C. Session model — DECIDED (2026-07-09)

One long-running Claude session for the whole queue, vs. **one session per offer**.
Per-offer is more robust (no context bloat, one bad page can't poison the rest) but
re-loads the playbook each time (small extra tokens). **Decision: one fresh agent per
offer** — robustness outweighs the re-load cost, and it maps cleanly to "each offer is
independent."

**Where it runs changed, the model did not.** The applier must run under **Cowork** (the
desktop app's local agent mode), because only Cowork's `claude-in-chrome` server can attach
a CV — it reads the file host-side and sends the extension base64 bytes, while the standalone
CLI forwards raw paths that the extension now rejects (measured 2026-07: same `file_upload`
tool name, different implementation — the CLI's forwards the path, Cowork's reads the bytes).

Cowork is one long-lived session, which naively would have destroyed the per-offer isolation
above. It does not, because **Cowork can spawn subagents** (verified 2026-07-09: subagents
spawn, and `file_upload` works inside them). So the model survives intact:

```
finder/ cockpit                         CODE — deterministic, zero agent tokens
  finder/data/offers_db.jsonl + src/applications_log.jsonl (joined for applied-status)
  → score + human picks the unapplied ones
  → src/worklist.json

Cowork parent agent = Orchestrator      PROSE — src/orchestrator_instructions.md
  reads worklist.json (never re-filters it)
  for each offer, sequentially:
      spawn a FRESH subagent  ← the per-offer isolation of this section
        subagent reads applier_instructions.md + profile.md
        drives one application in Chrome (isTrusted=true, §5B — same extension)
        uploads the CV (works here; fails under the CLI)
        appends its outcome to applications_log.jsonl
      verify the log line landed; pause 5–10 s
```

This is **strictly better than the old CLI `run_applier.ps1` loop** (now removed): same
isolation, plus a working CV upload.

### The mount boundary (§5D)
Cowork mounts **exactly one folder** and cannot read or write above it (measured 2026-07-10: a
session connected to a subfolder could not see its parent, and no `CLAUDE.md` was loaded). The
runtime files therefore live in **`src/`**, which is the folder the user connects; the design
docs and the whole `finder/` (its offer DB included) stay in the root, outside the agent's
filesystem.

This converts three prompt rules into geometry. "Do not read the offer DB" and the
CLAUDE.md context tax both disappear — the files are simply unreachable. What geometry cannot
express is `applications_log.jsonl`: it is an output, so it lives inside the mount, and the
orchestrator must read its last line to verify each outcome. Forbidden for dedup, required for
verification — a boundary is binary, so that one stays prose.

### Division of labour: code vs. prose
Deterministic work belongs in code; only reasoning belongs in an agent's context. An LLM
re-reading the whole log to compare URLs burns tokens *and* can miscompare — a set lookup
cannot. Hence:

| Concern | Lives in | Why |
|---|---|---|
| harvest, scoring, applied-status, worklist write | `finder/` (Python) | deterministic, exact, free |
| loop, subagent spawning, pacing, log verification | `orchestrator_instructions.md` | needs agent tools |
| form filling, free-text, blockers | `applier_instructions.md` | needs reasoning |
| facts | `profile.md` | unchanged by runtime |

### Two traps this model must respect
1. **The sandboxed shell.** Cowork's bash runs in a throwaway Linux VM. Whether writes to the
   mounted folder propagate back to Windows is **unverified**; a `>>` / `echo` redirect may be
   silently discarded. Logs must be written with the **file tools**, which always land. Stated
   in `orchestrator_instructions.md` §4 and `applier_instructions.md` §9 — deliberately phrased
   so it holds either way, so the question never has to be settled.
2. **Never drive the applier from the CLI.** Anything launching `claude -p` (the old
   `run_applier.ps1`, now removed) hits the broken upload path and silently fails to attach a
   CV. The applier runs only under Cowork.

### Pacing
Inter-offer delay is **5–10 s**, not the old 90 s jitter. Each application already takes 2–5
minutes and varies by form and composed text, so the submission interval is deeply irregular
before any jitter is added — extra randomness is theatre.

The control that actually binds is **volume**, which is what watcher #2 in §5B scores. There is
no automatic daily cap: the finder cockpit writes a worklist of exactly the offers the human
ticks, and already-applied offers are marked so they aren't re-picked. Volume is therefore
bounded per *batch*, not per *day*, and pacing across days is a human decision — several
back-to-back batches put several on the same calendar day. Past ~15/day the 5–10 s gaps should
come back up.

---

## 6. Phases

1. **Phase 1 — running.** Applier on justjoin.it internal-modal + external-ATS handling with
   the drive-to-success / log-or-block logic, review mode. Loop proven end-to-end.
2. **Phase 2 — built.** Finder over justjoin.it's JSON listings API (`finder/`).
3. **Phase 3 — next.** pracuj.pl support + richer dedup and reporting. Auto-submit once trust
   is proven; the prompt is being hardened separately in `trainer/`.

---

## 7. Open items (resolved during the build — kept as a record)

- **User stack + seniority** — .NET junior/mid; the finder's API query bakes this in.
- **CV variants** — four stacks under `src/CV_PDF/` (PL + EN each); mapping in
  `applier_instructions.md`.
- **Tone / default language** — decided: answer in the form's language, matching its register
  (`applier_instructions.md` §6).
- **Recon** — justjoin.it *does* expose a JSON listings API (`docs/JUSTJOIN_API_NOTES.md`);
  the internal modal and external-ATS flows are handled per `src/applier_instructions.md`,
  `src/portal_quirks.md` and `src/ats_quirks.md`.

---

## 8. Next steps

- Confirm the applier prompt reaches the `trainer/` "done" bar, then consider flipping
  `auto`-submit for the cleanest ATS paths.
- Extend the finder to pracuj.pl (the offer-id hash already ignores the source site, so the
  same job collapses across boards).
- Token-quality tuning still open: one chat per offer vs. several per chat; screenshot-loop
  vs. text-loop cost.