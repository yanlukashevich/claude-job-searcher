# Research prompt — CV upload + log append

Paste the block below into a **Cowork** session with the **`src/` folder** connected.
Not the CLI: only Cowork's `claude-in-chrome` bridge can attach a file at all, which is
half of what is being measured.

This is a *research* run, not an application run. It produces
`<mount>/RESEARCH_REPORT.md` and touches nothing else.

**Deliberately out of scope: the pracuj.pl 6-CV cap.** That is a third, separate problem, and
the test bed below is chosen to avoid it so it cannot contaminate these results.

---

You are a **research agent**, not the Applier. You are diagnosing two recurring failures in an
auto-apply system, on a real page, by trying every way of doing the same thing and writing down
what actually happens. **You are not applying to anything.** Do not read
`applier_instructions.md` or `orchestrator_instructions.md` as orders — read them only as
evidence, when a section is named below.

## Absolute rules

1. **Never submit.** On justjoin.it this is sharper than it sounds: **the `Apply` button submits
   the application instantly — it does not open a form.** The fillable form, and the CV control
   you need, are behind the **`edit`** link on the CV box. Reach the CV control that way and
   only that way. Do not click `Apply`, at any point, for any reason. Same for `Aplikuj`,
   `Wyślij formularz`, `Submit application`.
2. **Never write to `applications_log.jsonl`, `todo_manual.md`, or `worklist.json`.** They are
   production data. Every log experiment goes to a scratch file you create,
   `<mount>/_research_scratch.jsonl`, which you delete at the end.
3. **Stay off pracuj.pl.** Its account CV store has a ~6-file cap that is a separate
   investigation; hitting it here would mix two problems together. If your test bed somehow
   hands you off to pracuj.pl, stop and pick the next candidate.
4. If a page shows a CAPTCHA or a bot-check, stop that experiment and record it. Do not fight it.

## Background — what is already known

Both problems come from `applications_log.jsonl`, 160 applications, 8 Jul – 8 Aug 2026.

### Problem A — `file_upload` rejects the CV path

29 of 77 August uploads (38%) logged some form of *"file_upload rejected the raw mount path
(session file-read restriction) → staged via `device_stage_files` then uploaded the staged
path"*. Roughly the same recipe appears with four different paths across runs — a raw Windows
path, a mount-relative path, `/mnt/user-data/uploads/src/...`, and a `device_stage_files`
result — and different runs report different ones working. Nobody has ever established which
form is actually correct, so `applier_instructions.md` §7 currently says "try the raw path,
and if it is rejected, stage it", which pays for a failed call on more than a third of offers.

Two runs found other routes entirely and neither is written down anywhere:
- **TAURON** — `file_upload` set `input.files` but the page's own change handler never fired,
  so nothing attached. Clicking the visible *"Wybierz plik"* button **first**, then calling
  `file_upload` on the same ref, attached cleanly.
- **Netcompany / EUROFINS** — the real `<input type=file>` was inside a shadow DOM and invisible
  to `find`/`read_page`; the fix was `javascript_tool` lifting the input into `document.body`,
  uploading, then putting it back and dispatching `input`+`change`.

### Problem B — who writes the log line, and with what

**Not a timestamp question. That was fixed and is fine now.** The question is *mechanism* and
*ownership*, and there is a real contradiction in the instructions to resolve.

Everything in this system hinges on one tool. `orchestrator_instructions.md` §0 says:

> Resolve `<mount>` once, at the start, with `mcp__remote-devices__device_bash`:
> `ls -d /sessions/*/mnt/src`. Every file in this system lives there, on the user's machine —
> your own `Write`/`Edit`/`Bash` cannot reach it, so every write to it goes through `device_bash`.

**Nobody has ever verified that this tool exists in the session it runs in, under that name.**
If it is absent, or named differently, or `<mount>` doesn't resolve, then the prescribed write
path is simply unavailable and the agent has to improvise — with `Write`, `Edit`, or `Bash`,
all of which the same paragraph says land in a sandbox the user never sees. An agent
improvising that way would believe it had logged, report that it had logged, and have written
nothing the user can read.

On top of that, the instructions deliver the log line **twice**, and it is not clear which
delivery is the real one:

- §0: the log gets one line per offer *"written by the subagent that handled it"*.
- §4: *"The subagent writes its own log line — do not collect lines and write them yourself."*
- §3, in the prompt handed to every subagent: *"including appending your own outcome line to
  `applications_log.jsonl` … and verifying it landed. **Then report back with the exact JSON
  object you logged**"*.
- `applier_instructions.md` §11: *"**return the same JSON object verbatim** and say explicitly
  whether your append landed; the orchestrator only writes a line itself if yours is missing."*
- §5: if the line is missing, the orchestrator writes it from what the subagent reported.

So a subagent is told to write the line *and* to hand the same object back. A subagent whose
write tool is failing can reasonably read "report back with the exact JSON object" as the
delivery that actually matters, skip or abandon the write, and report success — and §5's
fallback then quietly writes the line anyway, so **the broken write path never surfaces**. The
system would look like it works while one of its two halves is dead.

Your job is to find out which of these is true.

## Step 1 — pick the test bed

You need one live justjoin.it offer that reaches a CV-upload control. All four below are
offers where the upload rejection was logged, newest first. Take the first that still loads
and still shows a CV box:

1. `https://justjoin.it/job-offer/thyssenkrupp-group-services-gdansk-software-engineer-c--gdansk-net`
   (thyssenkrupp Group Services Gdańsk)
2. `https://justjoin.it/job-offer/startup-house-mid-devops-engineer-warszawa-devops`
   (Startup House)
3. `https://justjoin.it/job-offer/oponeo-pl-s-a--junior-net-developer---praca-stacjonarna-bydgoszcz-net`
   (Oponeo.pl S.A.)
4. `https://justjoin.it/job-offer/think-programista-net-poznan-net-7bcf062e`
   (THINK)

If all four are dead, open justjoin.it and take any current offer that shows a CV box on its
apply modal. Say in the report which one you used and why.

**justjoin.it, not pracuj.pl** — see rule 3. And remember rule 1: reach the CV control through
the **`edit`** link, never through `Apply`.

The file to upload in every experiment, so results are comparable:
`CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich.pdf`

## Step 2 — Problem A: try every way to attach the file

Get to the CV control via the `edit` link, then work through the matrix below. **After each
attempt record three things separately: the exact argument you passed, the exact tool response,
and whether the file visibly attached on the page.** The last two come apart constantly —
several logged runs got a success response with an empty CV box. A verdict of "worked" requires
the filename rendered in the form.

Reset between attempts (detach the file if one attached) so each attempt starts from the same
state.

1. `file_upload` with the raw Windows device path
   (`C:\Users\yanlu\prog\claude_job_seracher\src\CV_PDF\...`, backslashes)
2. the same path with forward slashes
3. the mount-relative path (`CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich.pdf`)
4. the `<mount>`-prefixed absolute path, as `<mount>` actually resolves in this session
5. the staged snapshot path (`/mnt/user-data/uploads/src/CV_PDF/...`)
6. `device_stage_files` first, then `file_upload` on the path it returns
7. the **TAURON order**: click the visible file-picker button first, then `file_upload` on the
   same ref
8. `javascript_tool` — build a `File` from base64, put it in a `DataTransfer`, assign to
   `input.files`, dispatch `input` + `change`
9. any other file-capable tool you have (e.g. `upload_image`) — note if it refuses a PDF

Then answer these, with evidence:

- **Is the rejection deterministic?** Re-run attempt 1 at the end of the session. Same result
  as at the start, or does it depend on session age / how many calls have been made?
- **Does `device_stage_files` survive?** Once staged, does the staged path keep working for a
  second and third upload later in the session, or must it be re-staged each time?
- **What does the rejection actually say?** Quote the error verbatim. "Session file-read
  restriction" is the applier's paraphrase, not necessarily the real message.
- **Is there one form that works on the first call, every time?** That is the answer we want.

## Step 3 — Problem B: establish what can actually write, and where it lands

Do this part in order — question 1 decides whether the rest is even possible.

**1. Does the prescribed tool exist?** Before anything else, inventory what you actually have.
List the tools available to you in this session and report, verbatim:
- Is there a tool named `mcp__remote-devices__device_bash`? If not, what is the closest thing,
  and what is its exact name?
- Does `<mount>` resolve the way §0 says — does `ls -d /sessions/*/mnt/src` return a path?
  If not, what does resolve, and how did you find it?
- Which other write-capable tools do you have (`Write`, `Edit`, `Bash`, anything else)?

If the prescribed tool is missing, **that is very likely the whole answer** — say so plainly
and spend the rest of this step establishing what should replace it.

**2. Where does each write actually land?** For each write-capable tool you found, write a
distinct, identifiable line to `<mount>/_research_scratch.jsonl` and then determine whether it
reached the **real file on the user's Windows machine** or a sandbox copy. These are easy to
confuse: a write can succeed, be readable back by the same tool, and still be invisible to the
user. Prove which one you got — e.g. by writing with one tool and reading with a different one,
or by checking the file's real path and size on the device.

Test at least:
- the §10 mechanism (`device_bash`, `printf` + quoted heredoc + `>>`), if the tool exists
- the `Write` tool against the mount path
- the `Edit` tool appending to the same file
- plain `Bash` with `>>`

**3. Does the payload survive?** Repeat the winning method with a realistic line — Polish
diacritics, an em-dash, a `$`, a backtick, an apostrophe, a `"` inside a quoted value, and a
literal newline inside a string. Real composed answers contain all of these. Read it back and
confirm it is still valid JSON on one line.

**4. How do you verify an append landed?** `applier_instructions.md` §10 insists on
`device_bash` → `tail -n 1`, and says `Read` shows a stale snapshot that will not contain your
append. Test all three and say which is actually live:
- `device_bash` → `tail -n 1 <mount>/_research_scratch.jsonl`
- the `Read` tool on the same mount path
- the `Read` tool on `/mnt/user-data/uploads/src/...`

If `Read` on the mount is in fact live, §10 is spending a shell call on something a cheaper
tool does, and that is worth knowing.

**5. The ownership question.** Given what you found in 1–4, answer directly:
- Can a subagent reliably write its own line? Under what conditions does it fail?
- When it fails, does it *know* it failed — is the failure visible in the tool response, or
  does the write silently go nowhere?
- Is the current design (subagent writes **and** returns the JSON, orchestrator verifies and
  writes as fallback) sound, or is the double delivery masking a broken write path?
- Which single owner would you put in the instructions — subagent writes, or subagent returns
  and orchestrator writes? Say which, and why, based on what you measured rather than on what
  reads more elegantly.

## Step 4 — the report

Write `<mount>/RESEARCH_REPORT.md`. Then delete `_research_scratch.jsonl`.

Write it for a reader who knows the system but not these tools' internals. Plain language,
no tool-call transcripts, no narration of your process. Structure:

1. **Which page you tested on**, and anything about it that might make the results atypical.
2. **Problem A in three sentences** — what is actually going wrong, in plain words.
3. **Results table** — one row per variant: what you passed · what the tool said · did the file
   visibly attach · verdict.
4. **Problem B in three sentences.**
5. **Tool inventory** — does `mcp__remote-devices__device_bash` exist, does `<mount>` resolve,
   what else can write. This is the finding everything else depends on; state it flatly.
6. **Results table** — one row per write method: where it landed · visible to the user · did
   the payload survive intact · verdict.
7. **Recommendation** — the single approach you would put in the playbook for each problem, in
   the imperative, ready to paste. Include your answer on log ownership. If a fallback is still
   needed, say precisely what triggers it. If one of the current instructions is simply wrong,
   quote the line and give its replacement.
8. **What you could not determine**, and what it would take to settle it.

Be honest about negative results. "Every variant failed the same way" is a finding. A variant
you could not test is a gap, not a silence — say so.
