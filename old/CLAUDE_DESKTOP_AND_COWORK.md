# How Claude Desktop & "Cowork" work — and how they relate to this project

**Written 2026-07-09. Every claim here was verified on this machine (file inspection of the
desktop app's own session logs), except items explicitly marked "inference".**

This is a primer for a fresh chat where the goal is: *understand the Claude desktop app's
agent mode, and decide how to use it to run the auto-applier's CV upload.*

---

## 1. The three different "Claudes" on this machine

You actually have **three** distinct Claude runtimes installed, and they are easy to confuse
because some share tool names:

| # | What | Where it lives | How you use it |
|---|---|---|---|
| A | **Claude Code CLI** (standalone) | `C:\Users\yanlu\.local\bin\claude.exe` — **v2.1.204** | `claude` in a terminal; also the VS Code extension; also what `run_applier.ps1 → claude -p` launches |
| B | **Claude desktop app** | MSIX/Store app `Claude_pzs8sxrjxfjjc` (installed under `C:\Program Files\WindowsApps\…`, ACL-locked) | The "Claude" desktop application window |
| C | **"Cowork" = the desktop app's *local agent mode*** | Runs *inside* app B; sessions logged under `…\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\` | The agentic panel in the desktop app that drives your browser/files |

Key point: **B and C are the same app**; "Cowork" is a mode of the desktop app, not a
separate product. The desktop app bundles its **own** Claude Code engine — verified version
**2.1.202** (note: *older* than the standalone CLI's 2.1.204).

---

## 2. How Cowork (local agent mode) is built

From the desktop agent's own `init` record (verified in `audit.jsonl`):

- **Model:** `claude-opus-4-8`, `permissionMode: default`, `apiKeySource: none` (uses your
  logged-in Claude Pro session, not an API key).
- **Working directory:** a Windows path —
  `C:\Users\yanlu\AppData\Roaming\Claude\local-agent-mode-sessions\<a>\<b>\local_<c>\outputs`.
- **89 tools** across **11 built-in MCP servers**, all "connected":
  `claude-in-chrome`, `computer-use`, `cowork`, `cowork-onboarding`, `mcp-registry`,
  `plugins`, `scheduled-tasks`, `session_info`, `skills`, `visualize`, `workspace`.
  (Compare: the standalone CLI in this repo exposes ~22 tools from the single `chrome`
  server.) So the desktop agent is a much richer, self-contained environment.

### The split-brain execution model (this is the important bit)

Cowork runs across **two environments at once**:

```
   ┌─────────────────────────────┐        ┌────────────────────────────────────┐
   │  Linux sandbox (throwaway)  │        │  Your real Windows machine          │
   │  - runs Bash / code         │        │  - real logged-in Chrome            │
   │  - root fs: /bin /etc /mnt  │        │  - the file_upload host-side read   │
   │    /workspace /sessions …   │        │  - files under your connected repo  │
   └─────────────────────────────┘        └────────────────────────────────────┘
```

- **Shell / code execution → isolated Linux VM.** Verified: a Cowork session that ran `ls /`
  saw a Linux root (`bin boot dev etc home … mnt … workspace`), *not* `C:\`. This VM is
  disposable and walled off — it cannot see your Windows filesystem except folders that are
  mounted in.
- **Browser control + file_upload → your real Windows-side Chrome**, via the same
  claude-in-chrome extension mechanism (`fcoeoabgfenejglbffodgkkbkcdhcgfn`) that the CLI uses.
- **File tools** operate on Windows-style paths (`C:\Users\yanlu\...`) for the folder you
  connected to the session.

So when Cowork "uploads a file", the request is served on the Windows side, where the file
actually exists and where Chrome actually runs — not in the Linux VM.

---

## 3. Why file_upload WORKS in Cowork but FAILS in Claude Code CLI

This is the whole reason this doc exists. See also `FILE_UPLOAD_BUG_HANDOFF.md` and the
memory note `file-upload-broken-cli-extension-mismatch`.

**The chain for a browser file upload:**
```
model → file_upload(paths=…) → [claude-in-chrome server] → Chrome extension → web page
```

The **Chrome extension** was updated: it no longer reads file paths itself. It now requires
the caller to read the file and hand over its **bytes as base64** (`files:[{data,name,…}]`).
Raw `paths` are rejected: *"file_upload no longer accepts host filesystem paths…"*.

Now the difference — it's entirely in the **claude-in-chrome server** in the middle:

| | Claude Code CLI (A) | Cowork / desktop app (C) |
|---|---|---|
| Tool name | `mcp__chrome__file_upload` **and** built-in `mcp__claude-in-chrome__file_upload` | `mcp__claude-in-chrome__file_upload` |
| Backing code | `claude.exe 2.1.204` `--claude-in-chrome-mcp` (both servers = same binary) | desktop app's own bundled `claude-in-chrome` server |
| What it does with `paths` | **forwards the path** to the extension | **reads the file host-side → sends base64** |
| Result | extension rejects → fail | extension accepts → **"File Uploaded!"** |

**Proven, not guessed:**
- Cowork's `audit.jsonl` shows `mcp__claude-in-chrome__file_upload` called with
  `paths=[C:\Users\yanlu\prog\claude_job_seracher\CV_PDF\CV_Yan_Lukashevich_universal\CV_Yan_Lukashevich.pdf]`
  → *"Uploaded 1 file(s): CV_Yan_Lukashevich.pdf (99 KB)"* → page showed *"File Uploaded!"*.
- The standalone CLI (this repo's tool) was re-tested live the same day against the same
  page and still failed with the paths-deprecated error. Its binary contains
  `"Absolute paths to the files to upload"` but not `"Base64-encoded file contents"`.
- The user ran **both** CLI servers (`chrome` + built-in `claude-in-chrome`) in one session:
  **both failed identically**, because both are the same 2.1.204 binary.

**Two traps to remember:**
1. **Same tool name ≠ same code.** `mcp__claude-in-chrome__file_upload` exists in *both*
   products; it works in one and not the other because the server behind the name differs.
2. **Newer version ≠ the fix.** The *working* desktop agent is Claude Code 2.1.202, **older**
   than the failing CLI 2.1.204. The capability is in the claude-in-chrome server
   implementation, not the core version number.

### The "shared with this session" gate (applies in Cowork too)

Cowork does not let you upload *arbitrary* Windows files. Verified: it **rejected**
`C:\Windows\win.ini` with *"only files the user has shared with this session can be
uploaded"*, but **accepted** files under `C:\Users\yanlu\prog\claude_job_seracher\`. So the
rule is: the file must be inside a folder you connected to the agent session (your applier
repo qualifies) or a session output. This is a provenance check, and it's a *good* thing —
it's why an auto-applier can attach your CVs but not exfiltrate random system files.

---

## 4. What this means for the auto-applier

- `run_applier.ps1` launches `claude -p` = **runtime A (the CLI)** = the broken upload path.
  As built, the applier **cannot attach a CV**. That's the core problem to solve.
- **Cowork (runtime C) can attach CVs today**, from your repo folder, with the trusted
  (`isTrusted=true`) input path that ARCHITECTURE.md §5B requires. No JS `DataTransfer` hack
  needed (that one is banned anyway — it produces `isTrusted=false`).
- **Open design question for the new chat:** how to make the applier's per-offer loop run
  under Cowork instead of `claude -p`. Cowork is driven from the desktop app UI, not
  obviously from a script like `run_applier.ps1`. Things to investigate:
  - Does the desktop app expose any headless / scripted entry point, or is it GUI-only?
  - Can Cowork run the existing markdown "program" (`applier_instructions.md` + `profile.md`)
    as its task prompt, pointed at `offers_queue.json`?
  - Can its `scheduled-tasks` MCP server (seen in the init list) drive the queue on a timer?
  - Failing all that: keep `run_applier.ps1` for everything *except* CV-upload offers, and
    route only those through Cowork — or wait for a CLI build that gains the host-side read.

---

## 5. Quick verification commands (for the new chat, run from a Windows Git-Bash / terminal)

```bash
# The three runtimes
"C:/Users/yanlu/.local/bin/claude.exe" --version           # standalone CLI (A)
ls "$LOCALAPPDATA/Packages/Claude_pzs8sxrjxfjjc"            # desktop app data (B/C)

# Cowork session logs (its own audit trail of every tool call)
ls "$LOCALAPPDATA/Packages/Claude_pzs8sxrjxfjjc/LocalCache/Roaming/Claude/local-agent-mode-sessions"

# Prove the CLI binary lacks the base64 upload path
grep -c "Base64-encoded file contents" "C:/Users/yanlu/.local/bin/claude.exe"   # -> 0

# See how Claude Code CLI lists its servers
claude mcp list        # chrome (User) + built-in claude-in-chrome, both = same binary
```

---

## 6. One-paragraph summary

"Cowork" is the Claude **desktop app's local agent mode**: an Opus-4.8 agent whose *shell*
runs in a throwaway Linux VM but whose *browser and file uploads* act on your real Windows
Chrome and files, using 11 built-in MCP servers. Its `claude-in-chrome` server reads files
host-side and sends the browser extension base64 bytes, so **CV upload works**. The
standalone **Claude Code CLI** (what `run_applier.ps1` uses) has a `claude-in-chrome` bridge
that only forwards file *paths*, which the updated extension now rejects — so **CV upload
fails there**. Same tool name, different implementation; the desktop app is actually an
*older* Claude Code core (2.1.202 vs 2.1.204), so the fix is the upload bridge, not a version
bump. Next step: figure out how to run the applier's loop under Cowork.
