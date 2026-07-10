# `file_upload` handoff — why it fails here but works in Claude Cowork

> **RESOLVED 2026-07-09 — read this first.** Root cause confirmed from Cowork's own session
> logs, not inference. "Cowork" = the **Claude desktop app's local agent mode** running on
> this same machine. Its `claude-in-chrome` MCP server reads the file host-side and sends the
> extension base64 → **upload works** (it uploaded real CVs by path). The **Claude Code CLI**
> (`claude.exe 2.1.204`, used by both its `chrome` User-MCP and its built-in `claude-in-chrome`
> — same binary) only forwards the path → the updated extension rejects it → **fails**. Same
> tool name, different server implementation. NOTE: this is NOT a version bump — the *working*
> desktop agent runs Claude Code **2.1.202**, older than the failing CLI 2.1.204. Full
> architecture writeup: `CLAUDE_DESKTOP_AND_COWORK.md`. The "categorical rejection" framing
> below is superseded: `paths` works fine in the desktop app; it's the CLI's bridge that
> doesn't do the host-side read. Everything else below still stands.

**Date:** 2026-07-08
**Machine:** Windows 11, single machine. Both Claude products run on this same box.
**Symptom:** `mcp__chrome__file_upload` (claude-in-chrome MCP) cannot upload any file from
**this** session, but the user reports the **same tool works in Claude Cowork on the same
computer**. This document is a handoff for the Cowork instance to reproduce these checks on
its own side and explain the delta.

---

## TL;DR of the finding

- The **Chrome extension is shared** by both Claude products (same install, same version) —
  so the extension cannot be the difference.
- The **MCP controller is not shared** — it is bundled per Claude product. Here it is
  `claude.exe` **2.1.204**.
- Two distinct rejections were observed from this session, and **they come from two different
  layers**:
  1. `"file_upload no longer accepts host filesystem paths… pass its contents via the
     \`files\` parameter"` — this string lives in the **extension**.
  2. `"only files the user has shared with this session can be uploaded"` — this string lives
     in **`claude.exe`** (the controller), **not** the extension.
- Net: this session's controller (`claude.exe` 2.1.204) both (a) does not implement the new
  base64 `files` protocol the extension now wants, and (b) gates uploads behind a
  "shared-with-session" provenance check of its own.

**Hypothesis for Cowork to confirm/refute:** Cowork bundles a *newer/different MCP
controller* that (a) reads the file and sends base64 `files`, and/or (b) has a different
file-provenance model that treats project/scratchpad files as "shared." If Cowork can dump
its own controller version + the same strings below, we can pinpoint exactly which of the two
layers diverges.

---

## Environment facts (verified this session)

### MCP wiring
`chrome` MCP server is `claude.exe` launched with a flag — **the controller and the CLI are
the same binary**:

```
/mcpServers/chrome = {
  "type": "stdio",
  "command": "C:\\Users\\yanlu\\.local\\bin\\claude.exe",
  "args": ["--claude-in-chrome-mcp"],
  "env": {}
}
```
`claude mcp list` → `chrome: …claude.exe --claude-in-chrome-mcp - ✔ Connected`

### `claude.exe` (the MCP controller)
- Path: `C:\Users\yanlu\.local\bin\claude.exe`
- Size: 246,707,360 bytes, mtime 2026-07-08 06:10
- `claude --version` → **2.1.204 (Claude Code)**
- `claude update` → *"Claude Code is up to date (2.1.204)"* (nothing newer to install)

Strings embedded in `claude.exe` (via `grep -a`):

| String | In `claude.exe`? |
|---|---|
| `Absolute paths to the files to upload` | **PRESENT** (old `paths` schema) |
| `Only files the user has shared with this session` | **PRESENT** ← controller-side gate |
| `Base64-encoded file contents` | **absent** ← does NOT know the new `files` protocol |
| `no longer accepts host filesystem paths` | absent (that text is the extension's) |

### Chrome extension
- ID: `fcoeoabgfenejglbffodgkkbkcdhcgfn`
- Version on disk now: **1.0.80** (earlier this session 1.0.79 was also present; its
  `file_upload` handler was **byte-identical** in the relevant logic, so downgrading does not
  help).
- File holding the handler: `1.0.80_0/assets/mcpPermissions-DCTt63hZ.js`
- The `"no longer accepts host filesystem paths"` string is in **this extension file**.
- The `"shared with this session"` string is **NOT** in the extension (grep found nothing) —
  confirming that gate is controller-side.

### Extension's `file_upload` schema + validation (deobfuscated excerpt)
```js
files: {
  data:     { type:"string", description:"Base64-encoded file contents" },
  name:     { type:"string", description:"Filename shown to the page" },
  mimeType: { type:"string", description:"MIME type of the file" },
  required: ["data","name"],
  description:"Files to upload, as base64-encoded bytes. The MCP controller is responsible
               for reading the file and supplying its contents here."
},
paths: {
  type:"array", items:{type:"string"},
  description:"DEPRECATED. Host filesystem paths are no longer accepted; pass file contents
               via `files` instead."
},
ref:   { type:"string", ... },   // element ref from find/read_page
tabId: { type:"number", ... },

execute: async (e,t) => {
  const n = e;
  if (!n?.files || n.files.length === 0) {
    if (n?.paths && n.paths.length > 0)
      return { error: "file_upload no longer accepts host filesystem paths. The MCP
                       controller must read the file and pass its contents via the `files`
                       parameter. If you are seeing this in Claude Desktop, update the
                       desktop app." };
    throw new Error("files parameter is required and must be a non-empty array");
  }
  for (const f of n.files)
    if (typeof f.data !== "string" || typeof f.name !== "string" || !f.name)
      throw new Error("each file must have `data` and `name`");
  if (!n?.ref)   throw new Error("ref parameter is required");
  if (!t?.tabId) throw new Error(...);
  ...
}
```

**Key reading:** the extension's contract is unambiguous — send `files:[{data:<base64>,
name, mimeType}]`. `paths` is dead. Our controller (`claude.exe` 2.1.204) has no
`Base64-encoded file contents` code path, i.e. it cannot satisfy this contract.

---

## Live tests run this session (against a neutral sandbox)

Target: `https://the-internet.herokuapp.com/upload` (public file-upload test form), to avoid
touching any real job application. `find` located the `input[type=file]` as `ref_7`.

### Test 1 — real project path
```
file_upload(paths=["C:\\Users\\yanlu\\prog\\claude_job_seracher\\CV_PDF\\
                    CV_Yan_Lukashevich_python\\CV_Yan_Lukashevich_EN.pdf"], ref=ref_7)
→ ERROR: "file_upload no longer accepts host filesystem paths. The MCP controller must read
          the file and pass its contents via the `files` parameter…"
```

### Test 2 — file copied into the session scratchpad
```
copied CV → <session-temp>/scratchpad/cv_test.pdf   (93,734 bytes, confirmed on disk)
file_upload(paths=["…\\scratchpad\\cv_test.pdf"], ref=ref_7)
→ same host-filesystem-paths rejection.
```
⇒ Rejection is **categorical**, not a path-allowlist / location issue. Scratchpad (a
location historically described as "shared with the session") is rejected identically to the
project dir.

### Test 3 — try to use the extension's new `files` param directly
Attempted to pass `files:[{name,data(base64),mimeType}]`. The **client tool schema exposed to
this session only declares `paths`, `ref`, `tabId`** — there is no `files` field to fill.
Passing it anyway produced `"each file must have \`data\` and \`name\`"` even for an empty
array, which means the argument is not being forwarded in the shape the extension parses.
(NB: I could not fully prove *where* it is dropped — controller vs transport. This is the one
under-determined point; see "Open questions".)

### Test 4 — DOM `DataTransfer` injection via `javascript_tool` (mechanism sanity check only)
```js
const f = new File([bytes], 'probe.txt', {type:'text/plain'});
const dt = new DataTransfer(); dt.items.add(f);
input.files = dt.files;
input.dispatchEvent(new Event('change', {bubbles:true}));
// → { attached: 1, name: "probe.txt", size: 2 }  ✅ file attaches to the input
```
This proves a file *can* be placed into the input from the page context. **But** the
resulting `change` event is `isTrusted=false`. Per this project's `ARCHITECTURE.md` §5B, CV
attachment on a real ATS is a "sensitive moment" that must use the trusted-input path
(`isTrusted=true`). So this workaround is **rejected by policy**, not used. (An end-to-end
submit to confirm the injected file reaches the server was **not** performed — user stopped
it before that step.)

### Note on a second failure mode seen this session
At one point the rejection text was instead `"only files the user has shared with this
session can be uploaded."` That string is emitted by **`claude.exe`** (present in the
binary), i.e. the controller's own provenance gate, *before* the extension's base64 check is
even reached. So depending on inputs, a call can be blocked at **either** layer:
`controller provenance gate` → `extension base64 contract`.

---

## Why it likely works in Cowork (hypotheses to test on the Cowork side)

The only component that differs between the two products on this machine is the **MCP
controller binary**. So one or more of these must be true for Cowork:

1. **Newer controller implements the base64 `files` protocol.** Cowork's controller reads
   the file itself and sends `files:[{data,name,mimeType}]`, satisfying the extension. Test:
   does Cowork's controller binary contain the string `Base64-encoded file contents` (this
   one does **not**)?
2. **Different provenance model.** Cowork's controller does not apply (or applies a laxer)
   "shared with this session" gate, so project/scratchpad files count as shareable. Test:
   does Cowork's controller contain `Only files the user has shared with this session`, and
   under what condition does it throw it?
3. **Different tool schema exposed to the model.** Cowork exposes a `files` parameter on
   `file_upload` (this session only exposes `paths/ref/tabId`). Test: in Cowork, inspect the
   `file_upload` tool schema actually presented — does it have a `files` field?

---

## Exact checks to run on the Cowork side (mirror of what was done here)

Assuming Cowork is also driven by a `claude.exe`-style controller wired as the `chrome` MCP
server:

```bash
# 1. Which binary is Cowork's controller, and its version?
claude mcp list                     # find the `chrome` server command/path
"<that binary>" --version

# 2. Does Cowork's controller know the new protocol / the provenance gate?
grep -c "Base64-encoded file contents"                    "<controller binary>"
grep -c "Only files the user has shared with this session" "<controller binary>"
grep -c "Absolute paths to the files to upload"           "<controller binary>"

# 3. Same Chrome extension? (should be identical on this machine)
ls "$LOCALAPPDATA/Google/Chrome/User Data/Default/Extensions/fcoeoabgfenejglbffodgkkbkcdhcgfn"

# 4. What tool schema does Cowork expose for file_upload?
#    (Does it list a `files` param, or only `paths/ref/tabId`?)

# 5. Repeat the live test against the SAME neutral sandbox and capture the exact result:
#    navigate → https://the-internet.herokuapp.com/upload
#    find "file input" → ref
#    file_upload(<however Cowork expects>) → record success/exact error
```

Report back: controller **path + version**, the three `grep -c` counts, the extension version
string, and the exact `file_upload` result. Comparing those four numbers against this
document should isolate the single differing layer.

---

## Open questions (be honest about what is NOT proven)

- **Where exactly the `files` argument is dropped** in Test 3 (client tool layer vs MCP
  transport vs controller) is not proven. The empty-array symptom is consistent with "never
  forwarded" but a server-side guard could produce the same message; this was not
  disambiguated.
- **Whether the DataTransfer-injected file actually reaches the server** was not tested (no
  end-to-end submit). Only attachment-to-input was confirmed.
- **What "Cowork" is precisely** (separate product vs different launch mode of the same
  Desktop/Code stack) is not established from this side. The claim "different controller" is
  an inference from "same extension + different behavior," not a direct observation of
  Cowork's binary.

---

## Impact on this project

`file_upload` is the only method that yields a trusted (`isTrusted=true`) `change` event,
which `ARCHITECTURE.md` §5B requires for CV attachment. With it unusable from this session,
"form requires CV upload" is effectively a 4th manual blocker (log to `todo_manual.md`),
alongside CAPTCHA / forced-registration / missing-hard-fact. If Cowork's controller fixes
this, the right resolution is to **run the Applier under the Cowork controller**, not to fall
back to the policy-violating JS injection.
