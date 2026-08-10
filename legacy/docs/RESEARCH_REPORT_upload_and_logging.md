# Research report — CV upload rejection & log-write ownership

Research run, 9 Aug 2026. No application was submitted. Nothing outside this file and a
temporary scratch file was modified. pracuj.pl was not touched.

---

## 1. Which page was tested

**thyssenkrupp Group Services Gdańsk — Software Engineer C#** (candidate 1 on the list). It
loaded, and the CV control was reached through the `edit` link exactly as described. Three
things about it could make results atypical:

- The offer was **already applied to (08.08.2026)**, so the modal opened with a CV already
  attached (`Yan_Lukashevich_CV_EN.pdf`). That attachment was removed to get an empty control
  before each attempt, and the page was reloaded at the end — the offer still shows
  *Applied — 08.08.2026* with the original CV, unchanged.
- The file input is an ordinary, **visible** `<input type="file" name="attachment"
  accept="application/pdf,.pdf">` sitting in the normal page. It is **not** in a shadow DOM, so
  the Netcompany/EUROFINS problem cannot occur here, and there was nothing for the shadow-DOM
  workaround to fix.
- The page carries an **invisible reCAPTCHA** notice. No challenge was ever presented, so it did
  not interfere — but it means this form can in principle challenge a run.

The upload behaviour measured below is a property of the agent's own file access, not of
justjoin.it, so it generalises to every portal. The *event-handling* results (whether the form
notices an attached file) are specific to this page.

---

## 2. Problem A in three sentences

`file_upload` can only read files on the machine the agent itself runs on; `<mount>` is a
network mount of the user's Windows folder that exists only inside a *different* machine, the
one `device_bash` talks to. So no way of spelling the path to the CV — Windows-style,
mount-relative, or the full mount path — can ever work, because the file is simply not on the
machine doing the uploading. The only bridge between the two machines is `device_stage_files`,
which copies the file across; after that the copy uploads on the first try, every time.

The current instruction to try the raw path first is therefore not a heuristic that sometimes
wins — it is a call that **can never succeed**, paid on every offer.

---

## 3. Results — attaching the file

The file in every attempt: `CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich.pdf`
(101 320 bytes). The CV box was emptied between attempts. "Visibly attached" means the filename
and size rendered in the form, verified by screenshot *and* by reading the input's file list.

Every rejection returned the identical message, quoted verbatim:

> `Cannot upload "<path>": only files this session is allowed to read can be uploaded. Ask the user to share the file with this session, or to add its folder with /add-dir.`

Note this is **not** what the applier's log paraphrases it as. It says nothing about a
"session file-read restriction"; it suggests adding the folder, which is misleading — the folder
*is* connected, it is just connected to the other machine.

| # | What was passed | What the tool said | Visibly attached? | Verdict |
|---|---|---|---|---|
| 1 | `C:\Users\yanlu\prog\claude_job_seracher\src\CV_PDF\...\CV_Yan_Lukashevich.pdf` (backslashes) | rejection message above | No | **Fails** |
| 2 | `C:/Users/yanlu/prog/claude_job_seracher/src/CV_PDF/.../CV_Yan_Lukashevich.pdf` (forward slashes) | identical rejection | No | **Fails** |
| 3 | `CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich.pdf` (mount-relative) | identical rejection | No | **Fails** |
| 4 | `<mount>/CV_PDF/.../CV_Yan_Lukashevich.pdf` — i.e. `/sessions/rcw-01ky6f8gaqr15kezwdjfy5b9/mnt/src/...` | identical rejection | No | **Fails** |
| 5 | `/mnt/user-data/uploads/src/CV_PDF/.../CV_Yan_Lukashevich.pdf` (staged snapshot) | `Uploaded 1 file(s) to file input: CV_Yan_Lukashevich.pdf (99 KB total)` | **Yes** — `CV_Yan_Lukashevich.pdf 98.95 KB` | **Works** (only because the file had been staged earlier in the session) |
| 6 | `device_stage_files` first, then upload the path it returns | staging returned `/mnt/user-data/uploads/src/CV_PDF/.../CV_Yan_Lukashevich.pdf`; upload succeeded | **Yes** | **Works — this is the answer** |
| 7 | Click the visible file-picker button first, then upload (the TAURON order) | — | — | **Not tested — see §8** |
| 8 | Build the file in the page itself and hand it to the input, then fire the change events | input accepted it | **Yes** — form rendered the filename | Works, but **unnecessary here**; see caveat below |
| 9 | `upload_image`, targeting the same input, filename `CV_Yan_Lukashevich.pdf` | `Successfully uploaded image "CV_Yan_Lukashevich.pdf" (83KB) to file input` | **Yes — and this is the danger** | **Never use.** It did *not* refuse a PDF-only input. It attached a **JPEG screenshot** (magic bytes `ff d8 ff e0`, type `image/jpeg`) under a `.pdf` name, and the form displayed it as an attached CV. Both the tool and the page report success while the applicant's CV is a picture of a web page. |

Caveat on row 8: the page's own handler responds correctly to a programmatically attached file,
which is the thing the TAURON and Netcompany workarounds exist to fix. That mechanism is
therefore confirmed healthy on justjoin.it. The bytes used were a small stand-in rather than the
real 101 KB PDF, because pushing the whole file through that route is impractical — the test
proves the *event* path, not a real upload. It is a fallback for a broken page, never the
default.

### Three further measurements that pin down the cause

| What was passed | Result | What it proves |
|---|---|---|
| `/mnt/user-data/outputs/CV_out.pdf` — a copy never staged, sitting in the agent's own output folder | **Uploaded** | Permission is not per-file. Anything on the agent's own machine works. |
| `/home/claude/CV_home.pdf` — a copy in the agent's plain working directory | **Uploaded** (verified `%PDF-`, 101 320 bytes) | Confirms the same. The rule is *which machine*, not *which folder*. |
| `/mnt/user-data/uploads/src/CV_PDF/.../CV_Yan_Lukashevich_EN.pdf` — never staged, so absent | **Identical rejection message** | The error text **cannot distinguish "not allowed" from "not there"**. Do not read it as a permission problem. |

### The specific questions asked

**Is the rejection deterministic?** Yes, completely. Attempt 1 was re-run at the very end of the
session, roughly forty-five tool calls after the first, and returned a byte-identical error. It
does not depend on session age, call count, or warm-up. The variation across past runs was not
the tool behaving differently; it was different runs trying different paths.

**Does the staged file survive?** Yes. One staging call served **three separate uploads** spread
across the session, with page reloads in between, and no re-staging. Staging again is harmless
and returns the identical path, but it is a wasted call. Stage once per run.

**Is there one form that works on the first call, every time?** Yes — the staged path (rows 5/6).
It succeeded on every attempt, with no retry, and the file rendered in the form each time.

### One gotcha worth its own line

`device_stage_files` will **not** accept the `<mount>` path. Passing
`/sessions/.../mnt/src/CV_PDF/...` returns *"is not inside a folder connected to Cowork on this
device."* It wants the **Windows** path: `C:\Users\yanlu\prog\claude_job_seracher\src\CV_PDF\...`.
So the two tools that both deal with the user's files want the path in two different forms —
`device_bash` wants the mount path, `device_stage_files` wants the Windows path.

---

## 4. Problem B in three sentences

The prescribed tool exists and works, so the feared "the write path is simply unavailable"
scenario is not what is happening. But the trap it was worried about is real and worse than
expected: writing to a `<mount>` path with `Write` reports **"File created successfully"**, is
readable back with `Read`, and puts **nothing** on the user's machine — it silently invents a
private copy of the folder in the agent's own sandbox. Worse, once any agent has done that, a
plain shell `>>` to the same path stops failing loudly and starts succeeding into that phantom
folder too, so a subagent that reaches for the wrong tool can log all day and produce nothing.

---

## 5. Tool inventory — the finding everything else depends on

- **`mcp__remote-devices__device_bash` exists**, under exactly that name, immediately available
  without being loaded first. It exists **in spawned subagents too** — a subagent was spawned
  purely to check, reported the tool as immediately available, appended a line, and that line was
  then confirmed present by an independent check from the parent. §0's premise is sound.
- **`<mount>` resolves exactly as §0 says.** `ls -d /sessions/*/mnt/src` returned
  `/sessions/rcw-01ky6f8gaqr15kezwdjfy5b9/mnt/src`. The identifier is per-session, so it must be
  resolved fresh each run — §0 is right to insist on that rather than hard-coding it.
- The mount holds the real files: `applications_log.jsonl` (160 lines), the instruction files,
  `profile.md`, `worklist.json`, `todo_manual.md`, and `CV_PDF/`.
- **Other write-capable tools:** `Write`, `Edit`, and a plain shell — all three operate on the
  agent's own throwaway machine, which cannot see `/sessions` at all. Plus `device_stage_files`
  (user's machine → agent, read-only snapshot) and `device_commit_files` (agent → user's machine,
  whole files only, not appends).

**So the prescribed tool is not missing, and that is not the explanation.** The double delivery
is masking something, but not a dead tool — see §7.

---

## 6. Results — writing a line

All writes targeted `<mount>/_research_scratch.jsonl`. "Visible to the user" was proved by
writing with one tool and reading with a different one, and by checking the real file's size on
the user's machine.

| Method | Where it actually landed | Visible to user? | Payload intact? | Verdict |
|---|---|---|---|---|
| `device_bash`, quoted heredoc `<<'EOF'` (the §10 mechanism) | the real file on the Windows machine | **Yes** | **Yes — everything survived** | **Use this** |
| `device_bash`, `printf '%s\n' '<line>'` | the real file | **Yes** | Yes, but an apostrophe in the text must be escaped or the shell command breaks | Works; more fragile than the heredoc |
| `device_bash`, payload used as the `printf` format string | the real file | Yes | **No — corrupted** | **Never.** A `\n` inside a value became a real line break, splitting one record into two lines, both invalid JSON. |
| `Write` on the mount path | a **phantom folder** invented inside the agent's own sandbox, containing only that file | **No** | n/a | **Silent total failure.** Reported *"File created successfully."* |
| `Edit` appending to the same path | the same phantom file | **No** | n/a | **Silent total failure.** Reported *"has been updated successfully."* |
| Plain shell `>>`, before any `Write` had run | nowhere | No | n/a | **Fails loudly** — *"No such file or directory"*, non-zero exit. Safe. |
| Plain shell `>>`, **after** a `Write` had created the phantom folder | the phantom file | **No** | n/a | **Silent failure.** Exit 0. This is the cascade: one `Write` converts an honest error into a silent one for the rest of the session. |

Through every one of those `Write`/`Edit`/shell operations, the real file on the user's machine
stayed at **two lines** — the two written by `device_bash`.

**Payload survival (question 3).** A realistic line was written with the heredoc containing
Polish diacritics (`Żabka`, `Gdańsk`, `ąćęłńóśźż`), an em-dash, `$0` and `$HOME`, backticks, an
apostrophe (`it's Yan's CV`), an escaped quote inside a value (`powiedział \"tak\"`), and a `\n`
inside a string. Read back, it parsed as valid JSON on one line with every character intact,
including `$HOME` unexpanded and the `\n` preserved as an escape rather than an actual break.
The quoted heredoc is genuinely safe for composed answers.

**Verification (question 4) — §10 is right, and it is not wasteful.**

| Method | Live or stale |
|---|---|
| `device_bash` → `tail -n 1 <mount>/...` | **Live.** Always showed the newest line. |
| `Read` on the `<mount>` path | **Neither** — *"File does not exist."* It cannot see the user's machine. And if a `Write` has created the phantom copy, `Read` happily returns *that*, which is worse than failing. |
| `Read` on `/mnt/user-data/uploads/src/...` | **Stale, exactly as §10 warns.** A line appended after staging was invisible to it. |

So §10's insistence on a second `device_bash` call is correct and should stay. There is no
cheaper tool that does the job.

**Concurrency.** Forty simultaneous appends to one file on the mount produced forty valid,
distinct, uncorrupted JSON lines with none lost or interleaved. Parallel subagents appending to
`applications_log.jsonl` is safe.

**One operational limit found by accident:** files on the mount **cannot be deleted** — `rm`
returns *"Operation not permitted."* `mkdir`, `mv`, and truncating to empty all work. Anything
that needs removing has to be emptied and moved aside, not deleted.

---

## 7. Recommendation

### Problem A — replace applier_instructions.md §7

This line is simply wrong and should go:

> "If `file_upload` **rejects the raw path** (a session file-read restriction), stage the file
> with `device_stage_files` and upload the staged path."

It describes the failure as conditional. It is not: the raw path is rejected 100% of the time,
so this instruction buys a guaranteed-wasted call on every single offer, and its parenthetical
misnames the cause. Replace it with:

> **Stage the CVs once, at the start of the run, then upload staged paths.**
>
> `file_upload` reads only from your own machine. `<mount>` is on the user's machine. No spelling
> of the CV's path — `C:\...`, `C:/...`, mount-relative, or `<mount>/...` — will ever work. Do not
> try the raw path first; it is not a heuristic, it is a guaranteed failure.
>
> 1. Once per run, before the first offer, stage every CV variant in one call —
>    `device_stage_files` with the **Windows** paths, `C:\Users\yanlu\prog\claude_job_seracher\src\CV_PDF\...`
>    (not the mount path — staging rejects that). It accepts up to 50 files per call.
> 2. It returns a `stagedPath` for each, of the form
>    `/mnt/user-data/uploads/src/CV_PDF/<variant>/<file>.pdf`. Upload **that** path with
>    `file_upload`. It works on the first call.
> 3. One staging call lasts the whole run — the staged CVs serve every offer. Do not re-stage
>    per offer.
> 4. **A success response is not proof.** Confirm the form renders the filename before moving on.
> 5. Never use `upload_image` for a CV. It does not refuse a PDF-only input — it attaches an
>    image under whatever name you give it and reports success, so the applicant sends a
>    screenshot instead of a CV.
>
> If a form still shows nothing after a successful upload, the page's own handler is not firing.
> Only then: click the visible file-picker button first and upload again; if the input cannot be
> found at all, it is inside a shadow DOM and must be lifted out, uploaded to, and put back.
> Both are rescue procedures, not steps.

Keep §7's *"Don't verify the file exists — just upload it"* — but note that a **missing** file
and a **forbidden** path give the identical error, so "file missing" can no longer be diagnosed
from the message. With staging, `device_stage_files` reports per-file success, and that is where
a genuinely missing CV will surface.

### Problem B — log ownership: **the subagent writes.** Keep §0, §4 and §10.

Not because it reads better, but because it is what the measurements support: `device_bash` is
present in subagents, the append lands, verification is one cheap call, and forty concurrent
appends did not corrupt or lose a line. Centralising the write in the orchestrator would buy
nothing and would risk losing lines if the orchestrator's own context is trimmed mid-run, while
the subagent holds the outcome at the moment it is freshest.

**But the double delivery is masking something, and the fix is to make the fallback loud.** The
suspected mechanism was slightly wrong: the danger is not a subagent whose write tool is missing.
It is a subagent that reaches for `Write` or `Edit` instead of `device_bash` — those report
success, `Read` confirms the phantom file, and the subagent can honestly believe and honestly
report that it logged. §5's fallback then writes the line anyway and the broken subagent looks
fine. That is exactly the invisible half-dead system described, arrived at by a different route.

So keep the structure but change what happens on the fallback path. Replace this in §11:

> "the orchestrator only writes a line itself if yours is missing."

with:

> "The orchestrator writes the line itself if yours is missing — **and records that your append
> failed.** A missing line is not a routine top-up; it means that subagent's write path is
> broken, and it must be surfaced in the run summary, not silently patched."

And add one sentence to §10, since it is the actual failure mode:

> "Use `device_bash` and nothing else. `Write` and `Edit` on a `<mount>` path report success and
> write to a private copy the user will never see — and once they have, a plain shell `>>` to that
> path silently succeeds too. If your `tail -n 1` does not show your line, say so plainly in your
> report; do not retry with `Write`."

**What triggers the fallback:** only the orchestrator's own `tail -n 1` failing to find the
subagent's line. Never the subagent's self-report — the whole point is that a subagent using the
wrong tool reports success in good faith.

---

## 8. What could not be determined

**The TAURON pre-click (row 7) was not tested.** On this page the file input is the visible
control itself, so clicking it opens a native Windows file-picker dialog — a window the browser
tools cannot see, cannot close, and which blocks every subsequent command. Attempting it risked
losing the session and every result in this report. It was also unobservable here for a second
reason: the page's change handler already fires correctly on a programmatic upload (row 8), which
is the exact fault the pre-click exists to work around, so there was nothing for it to fix. To
settle it properly, run it on a page that reproduces the TAURON symptom — a successful upload
response with an empty CV box — where the pre-click has a visible effect, and where the picker
can be dismissed by hand if it opens.

**Row 8 used stand-in bytes.** The event mechanism was tested faithfully; a real 101 KB PDF
through that route was not. This only matters if that fallback is ever needed for real, and the
fix is to carry the file across in chunks and check the resulting size.

**Whether these results hold on other portals is untested by design.** The upload findings are a
property of the agent's file access and will hold anywhere. The event-handling findings are
specific to this page — a form that fails to notice the attachment (the TAURON symptom) is still
possible elsewhere, which is why the rescue procedures stay in the playbook.

**One offer, one session.** The rejection was deterministic across the session, but a second
session on a different day was not run. Nothing observed suggests it would differ.

**The pracuj.pl CV cap was deliberately not investigated** and nothing here speaks to it.
