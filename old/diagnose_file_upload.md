# Diagnostic: how does CV upload actually work in your auto-applier?

**How to run this:** open Claude Code in your applier's repo and paste:

> Read `diagnose_file_upload.md` and follow it exactly.

---

## Ground rules (obey these strictly)

- **Read-only.** Do not modify, create, or delete any file except the single report file
  named in §7. Do not `git commit`.
- **Do not submit any job application.** Do not click Apply or Submit anywhere.
- **Do not install, update, or downgrade anything.** No `claude update`, no npm, no
  extension changes.
- **Evidence, not memory.** Every claim must be backed by a command you actually ran and
  whose output you paste. If you cannot verify something, write `UNKNOWN`. Never guess,
  never fill a gap with what "should" be true.
- If a command fails, paste the error rather than silently trying a different one.

---

## Background: what we're trying to explain

On another machine, `file_upload` (Claude-in-Chrome MCP) **cannot upload any file**. Two
distinct failure modes were observed there, at different times, on the same CLI version:

**Failure mode A — deprecated `paths` parameter:**
```
file_upload no longer accepts host filesystem paths. The MCP controller must read the
file and pass its contents via the `files` parameter.
```
The extension bundle wants `files: [{data: <base64>, name, mimeType}]`. That machine's
`claude.exe` (2.1.204) has no `files` support — the string `"Base64-encoded file contents"`
is absent from the binary, while `"Absolute paths to the files to upload"` is present.

**Failure mode B — attachment-provenance check:**
```
Cannot upload ...: only files the user has shared with this session can be uploaded.
```
Rejected identically for a file in the project root, a file in the session scratchpad, and
a genuine chat attachment.

Your applier reportedly works. **We need to know exactly why.** The likely explanations,
which this diagnostic must discriminate between:

1. Your CLI is a **different version** that sends base64 `files`.
2. Your **extension predates** the breaking change and still accepts `paths`.
3. **No upload ever happens** — the site attaches a CV already saved in your
   justjoin.it / pracuj.pl *account profile* ("use saved CV"), so no file input is touched.
4. Different **client wiring** (Claude Desktop vs bare CLI vs IDE extension).
5. **JS injection** (`input.files = dt.files` + synthetic `change` event).
6. **External tooling** (Playwright, Selenium, AutoHotkey, native file-picker automation).
7. Something else.

Hypothesis **3** is considered most likely. Do not let that bias you — test it, don't
assume it.

---

## §0. YOUR SETUP: macOS + Claude Desktop

You are on **macOS**, running **Claude Desktop**. That matters enormously, because the
extension's own error message says:

> *"If you are seeing this in Claude Desktop, **update the desktop app**."*

This means **the Desktop app is the "MCP controller"** that is supposed to read the file and
pass base64 `files`. The broken machine is a Windows `claude.exe` CLI. **Your Desktop app
may simply be a build that already implements the new API** — that would be hypothesis 1,
and it would be the whole answer.

So: the version that matters for you is the **Claude Desktop app version**, not a CLI
version. §4 greps the app bundle, not `claude`.

## §1. Client & versions

```bash
# Desktop app version — THE important one
defaults read /Applications/Claude.app/Contents/Info.plist CFBundleShortVersionString
defaults read /Applications/Claude.app/Contents/Info.plist CFBundleVersion

# CLI, only if you also have it
claude --version 2>/dev/null || echo "no claude CLI"
claude mcp list 2>/dev/null || echo "no claude CLI"
which claude

sw_vers   # macOS version
```

Report:
- **Claude Desktop app version** (both `CFBundleShortVersionString` and `CFBundleVersion`).
- Whether a `claude` CLI also exists, and its version.
- If `claude mcp list` works: the **full command + args** of the Chrome MCP server.
- If Desktop reaches Chrome **without** a `claude mcp` entry, say so — that means the MCP
  bridge is built into the Desktop app, which is itself a key finding.
- macOS version.

## §2. Which Claude-in-Chrome extension version is installed

Extension id: `fcoeoabgfenejglbffodgkkbkcdhcgfn`

```bash
ls -1 ~/Library/Application\ Support/Google/Chrome/*/Extensions/fcoeoabgfenejglbffodgkkbkcdhcgfn/
```

(The `*` covers `Default`, `Profile 1`, etc. — report **which profile** you actually use in
Chrome, since you may have several. If you drive a non-default profile, that's the one that
matters.)

List **every** version subdirectory present.

Also report: is the extension loaded **unpacked**, pinned by **MDM/enterprise policy**, or
is Chrome auto-update disabled? Check `chrome://extensions` with developer mode on, and:

```bash
ls /Library/Managed\ Preferences/com.google.Chrome.plist 2>/dev/null && echo "MDM policy present"
```

## §3. THE KEY QUESTION — does your extension still accept `paths`?

In the **newest** version directory (substitute your profile and version):

```bash
EXT=~/Library/Application\ Support/Google/Chrome/Default/Extensions/fcoeoabgfenejglbffodgkkbkcdhcgfn/<VERSION>
grep -rl "no longer accepts host filesystem paths" "$EXT"
grep -rl "Base64-encoded file contents" "$EXT"
grep -rl "only files the user has shared with this session" "$EXT"
```

Interpret:
- **All three absent** → your extension predates both breaking changes. **This is very
  likely the answer.** Report the exact version number. Your setup will break the moment
  Chrome auto-updates it.
- **First two found** → your extension also rejects `paths` (failure mode A). Then your
  applier is *not* uploading via `file_upload`+`paths`, and §5 must explain what it really
  does.
- **Third found** → failure mode B is present. Same conclusion: §5 must explain it.

If you find the handler, paste the ~600 characters of minified code around the match so we
can read its actual validation logic.

## §4. THE DECISIVE TEST — does your Desktop app know about base64 `files`?

This is the most important section. The Desktop app is the MCP controller. If **it** knows
the new API, everything is explained.

Grep the whole app bundle (JS is inside `app.asar` / `.asar.unpacked`; `grep -ra` handles
both, and `strings` covers the native binary):

```bash
APP=/Applications/Claude.app

grep -ra "Base64-encoded file contents"            "$APP" | head -3
grep -ra "Absolute paths to the files to upload"   "$APP" | head -3
grep -ra "Only files the user has shared with this session" "$APP" | head -3
grep -ra "file_upload"                             "$APP" | head -3
```

If `app.asar` is packed and greps come back empty, extract and retry:

```bash
npx asar extract "$APP/Contents/Resources/app.asar" /tmp/claude_asar 2>/dev/null \
  && grep -ra "Base64-encoded file contents" /tmp/claude_asar | head -3
```

Also grep the **CLI binary**, if you have one, for comparison:

```bash
B=$(which claude); grep -ac "Base64-encoded file contents" "$B"; grep -ac "Absolute paths to the files to upload" "$B"
```

Report each string as PRESENT / ABSENT, **for the app bundle and the CLI separately**.

Interpretation:
- `"Base64-encoded file contents"` **PRESENT in the Desktop app** → your Desktop app
  implements the new API. **Hypothesis 1 confirmed.** Say so loudly, report the app version
  from §1 — that version number is exactly what the broken machine needs.
- **ABSENT in the app**, yet your applier still attaches CVs → the upload is not going
  through `file_upload` at all. §5 must explain it.

## §5. What does your applier ACTUALLY do for the CV? (do not assume)

1. Grep your applier instruction/prompt files for each of:
   `file_upload`, `upload`, `CV`, `resume`, `attach`, `DataTransfer`, `input[type=file]`,
   `saved CV`, `zapisane CV`.
   **Quote the relevant lines with file:line.**

2. Grep your run logs / transcripts for real `file_upload` tool calls.
   - Did one ever **succeed**? Paste one successful call **with its arguments and its
     result**, verbatim.
   - If every occurrence is an error, say so and paste the most recent error.
   - If there are **zero** `file_upload` calls in your entire log history, that is a major
     finding — state it explicitly.

3. **CRITICAL — is a file uploaded at all?** Inspect your applier's flow and a recent
   successful application log. Determine whether the form:
   - (a) uploads a file from disk into an `<input type=file>`, **or**
   - (b) selects a CV already stored in your justjoin.it / pracuj.pl account profile
     (a "use saved CV" / "wybierz zapisane CV" radio or dropdown).

   If **(b)**, there is no file upload happening anywhere, and that alone explains why your
   applier works while `file_upload` is broken. Quote the log lines proving it.

4. If you attach the file with JavaScript (`input.files = dt.files` followed by
   `dispatchEvent(new Event('change'))`), say so explicitly and **quote the code**.
   Also report whether you ever checked `event.isTrusted` on that change event.

5. Any non-Claude tooling anywhere in the CV-attach path? (Playwright, Selenium,
   AutoHotkey, Puppeteer, a native file-picker driver, `xdotool`, …)

## §6. Live confirmation — safe sandbox, no application submitted

Do this. It answers the whole question in one shot, independent of what your applier does.

1. Open a new tab to `https://the-internet.herokuapp.com/upload` (a neutral sandbox).
2. `find` the `input[type=file]` element to get its `ref`. **Do not click it** — clicking a
   file input opens a native macOS dialog you cannot control.
3. Call `file_upload` with that `ref`, **three times**, and paste the verbatim result of
   each:
   - **6a.** an absolute path to a file in the repo, e.g. `/Users/<you>/.../CV.pdf`
   - **6b.** an absolute path to a file in `/tmp`
   - **6c. Desktop-only, the interesting one:** *first* drag-and-drop or paste a PDF as a
     **chat attachment** into this very conversation, *then* call `file_upload` for it.
     Report what path (if any) you can even name for that attachment, and whether the call
     succeeds.

§6c matters because the extension's rejection on the broken machine was
*"only files the user has shared with this session"* — implying an attachment-provenance
check rather than a path allowlist. On Windows the attachment never lands on disk as a
plain file, so no path could name it. **If 6c succeeds on macOS Desktop, that is the
mechanism**, and it's what the broken setup lacks.

For each of 6a/6b/6c report: SUCCESS, or the **exact** error string.

---

## §7. Write the report — ONE standalone file, safe to send

**The deliverable is a single file: `file_upload_diagnosis_report.md` in the repo root.**
Your friend will send *only this file* to someone else. Therefore:

### Sanitize before writing (mandatory)
- Replace the macOS home directory with `~` everywhere. No real username in any path.
- **Never** include: real name, email, phone, address, salary, notice period, or any other
  content from `profile.md` / the CV.
- **Never** include job-offer URLs, company names, or recruiter details from the logs.
  Redact them as `<offer-url>`, `<company>`.
- Do not paste the CV file's contents or base64 anywhere.
- Do not include API keys, tokens, session ids, or OAuth credentials. If a command's output
  contains one, replace it with `<redacted>`.
- If a log line proves a point but carries personal data, quote **only** the part that
  proves it, and mark the removal: `... <redacted> ...`.

Everything the report needs is *mechanism*, never *content*. A path, a version number, a
tool name, an error string — none of those require personal data.

### Make it self-contained
Whoever reads this file will not have your machine, your repo, or this prompt. So:
- Paste **raw command output**, not summaries of it. "Grep found it" is useless; the actual
  line is what we need.
- Say which command produced each block.
- Include the failing/succeeding `file_upload` calls **verbatim**, arguments included
  (paths sanitized to `~/...`).
- If you skipped a section, write `NOT RUN` and why. Don't silently omit it.

### Structure

```markdown
# file_upload diagnosis report
Generated: <date>  •  Machine: macOS + Claude Desktop

## Verdict
Which is true (pick one, cite the decisive evidence):
  1. Desktop app implements base64 `files` (report its exact version!)
  2. Older extension that still accepts `paths`
  3. No upload happens — CV attached from saved account profile
  4. Upload only works for files shared as a chat attachment (§6c)
  5. JS injection
  6. External tooling
  7. Something else

## Decisive evidence
<the single command output or log line that proves the verdict, verbatim>

## Does this transfer to a Windows + claude.exe CLI machine?
<yes / no / unknown — and why. If the mechanism is "saved CV in account profile" or
"pinned old extension", say plainly that it does NOT transfer as a fix.>

## §1 Environment
- Claude Desktop version (CFBundleShortVersionString / CFBundleVersion):
- claude CLI present? version:
- Chrome MCP server command (or "built into Desktop, no mcp entry"):
- macOS version:

## §2 Extension versions on disk
<raw ls output; which Chrome profile; pinned/unpacked/MDM?>

## §3 Extension grep results
<raw output of all three greps + the ~600 chars of handler code if found>

## §4 Desktop app bundle grep results  (THE decisive test)
- "Base64-encoded file contents": PRESENT / ABSENT
- "Absolute paths to the files to upload": PRESENT / ABSENT
- "Only files the user has shared with this session": PRESENT / ABSENT
<raw output>
CLI binary, for comparison: <same three, or "no CLI">

## §5 What the applier really does
<quotes with file:line; the (a)/(b) answer; a verbatim successful CV-attach log line if one
exists, personal data redacted>
Count of `file_upload` calls found in all logs: <n>  (if 0, say so loudly)

## §6 Live sandbox test (the-internet.herokuapp.com/upload)
- 6a repo path:        SUCCESS / <exact error>
- 6b /tmp path:        SUCCESS / <exact error>
- 6c chat attachment:  SUCCESS / <exact error>   ← most interesting
<what path, if any, could even name the attachment>

## UNKNOWNs
<everything you could not confirm — be exhaustive here>
```

### Finally
1. Confirm in chat that the file is written, and print the **Verdict**, **Decisive
   evidence**, and **Does this transfer?** sections so they can be read at a glance.
2. Re-read the file once and confirm out loud: *"checked for personal data: none present"*
   — or fix it and say what you removed.

**Do not speculate anywhere in the report.** An honest `UNKNOWN` is far more useful than a
plausible-sounding guess — the people reading this have already been burned twice by
confident theories that turned out wrong. If §4 and §6 contradict each other, report the
contradiction rather than picking a winner.
