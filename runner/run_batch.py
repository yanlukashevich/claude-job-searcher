#!/usr/bin/env python
"""Run the applier over `runner/data/worklist.json`, one offer at a time.

Replaces the Cowork orchestrator (`src/orchestrator_instructions.md`). Everything that file
did is deterministic - read a JSON list, iterate, launch one agent per offer, check that a log
line arrived - so it is code here instead of an LLM.

    python runner\\run_batch.py [--mode review|auto] [--pick 3-5] [--limit N] [--dry-run]

The applier is launched with `claude -p` and no write tools at all: it reads files, drives
Chrome, and returns one JSON object matching `log_line.schema.json`. This runner stamps the
time and does every write - so the timestamp is real, a half-written line is impossible, and
the agent physically cannot touch the audit trail.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
RUNNER = ROOT / "runner"

DATA = RUNNER / "data"

# The queue, the audit trail and the manual to-do list belong to the runner, not the applier:
# code writes and reads them, and `src/` stays prompts-only so the agent never finds them.
WORKLIST = DATA / "worklist.json"
LOG = DATA / "applications_log.jsonl"
TODO = DATA / "todo_manual.md"

MCP_CONFIG = RUNNER / "applier_mcp.json"
SCHEMA = RUNNER / "log_line.schema.json"
RUN_LOG = DATA / "run_log.jsonl"
AUTOCLICK = RUNNER / "permission_autoclick.py"
AUTOCLICK_LOG = DATA / "autoclick.log"

# The CLI writes each run's trace here and deletes it 30 days later (`cleanupPeriodDays`);
# every number stats.py reports that the result envelope does not carry lives in that file.
PROJECTS = Path.home() / ".claude" / "projects"
TRANSCRIPTS = DATA / "transcripts"

START_CHROME = ROOT / "tools" / "mcp_webfile" / "start_chrome.ps1"
CDP_URL = "http://127.0.0.1:9222/json/version"

# Field order on disk, matching the lines already in applications_log.jsonl.
LOG_FIELDS = [
    "url", "company", "title", "apply_type", "outcome", "cv_used",
    "composed_answers", "blocked_reason", "notes", "diagnostics",
]

PROMPT = """You are the Applier. Apply to ONE job offer for Yan Lukashevich by driving his
logged-in Chrome via the claude-in-chrome tools.

Read and follow these two files in your working directory, exactly:
  - applier_instructions.md   (your operating manual: behavior, rules, the loop, the fields)
  - profile.md                (the sole source of truth for every fact)

Run mode: {mode}   (review = fill everything, then STOP before Submit; auto = fill and Submit)

The one offer to handle:
{offer}

Absolute path of your working directory, for tools that need one (mcp__webfile__attach_file
takes an absolute path; profile.md gives CV paths relative to it):
{src}

You have no write tools: you write nothing to disk, and there is no log file to append to.
Report your outcome by returning a single JSON object in the enforced output schema - the same
fields section 10 of the playbook describes. The runner stamps the time and writes the log line
and, if you are blocked, the todo_manual.md entry. Fill `diagnostics` on every run, and put
every free-text you composed verbatim in `composed_answers`, review mode included.
"""


# --------------------------------------------------------------------------- chrome

def cdp_alive(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(CDP_URL, timeout=timeout) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def ensure_chrome(wait_s: int = 45) -> bool:
    """Bring up the chrome-mcp profile with the DevTools port open, if it isn't already."""
    if cdp_alive():
        print("chrome   CDP port 9222 already answering")
        return True

    print(f"chrome   port 9222 silent -> {START_CHROME.name}")
    # The script blocks while Chrome runs, so it has to be detached.
    inner = ("-NoProfile','-ExecutionPolicy','Bypass','-File','" + str(START_CHROME))
    subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
         "Start-Process powershell -WindowStyle Minimized -ArgumentList '" + inner + "'"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if cdp_alive():
            print("chrome   up")
            return True
        time.sleep(1.5)
    return False


def venv_python() -> str:
    """The interpreter that has `websockets`, which the autoclicker needs."""
    inside = ROOT / ".venv" / "Scripts" / "python.exe"
    return str(inside) if inside.exists() else sys.executable


def start_autoclick():
    """Answer the extension's site-permission card for the length of the batch.

    The extension keeps a per-domain allowlist of its own, and `bypassPermissions` does not
    reach it - the refusal happens in the browser, not in Claude Code. Unattended, the first
    employer ATS the applier is handed off to stops the batch behind a dialog nobody clicks.
    Which domains it approved is in runner/data/autoclick.log."""
    if not AUTOCLICK.exists():
        print("chrome   no permission_autoclick.py - new domains will stop the batch")
        return None
    handle = AUTOCLICK_LOG.open("a", encoding="utf-8", buffering=1)
    handle.write("\n--- batch started {}\n".format(now_warsaw()))
    proc = subprocess.Popen([venv_python(), str(AUTOCLICK)],
                            stdout=handle, stderr=subprocess.STDOUT)
    print("chrome   site-permission autoclick up (pid {}) -> {}"
          .format(proc.pid, AUTOCLICK_LOG.name))
    return proc


# --------------------------------------------------------------------------- applier

def claude_exe() -> str:
    found = shutil.which("claude")
    if found:
        return found
    fallback = Path(os.environ["USERPROFILE"]) / ".local" / "bin" / "claude.exe"
    if fallback.exists():
        return str(fallback)
    sys.exit("claude CLI not found on PATH")


def build_cmd(schema_text: str, model: str) -> list:
    # --tools and --mcp-config are variadic, so they must never be last: they would eat
    # whatever follows. The prompt goes on stdin for the same reason.
    return [
        claude_exe(), "-p",
        "--model", model,
        "--setting-sources", "",              # no CLAUDE.md, no user settings, no user MCP
        "--strict-mcp-config",
        "--mcp-config", str(MCP_CONFIG),      # chrome + webfile; mandatory, not hygiene
        "--tools", "Read", "Glob",            # built-ins only: no Write/Edit/Bash
        "--permission-mode", "bypassPermissions",
        "--disable-slash-commands",
        "--output-format", "json",
        "--json-schema", schema_text,
    ]


def ps_cmdline(cmd: list) -> str:
    """Render a command for pasting into PowerShell. It drops a bare "" before the exe ever
    sees it - so `--setting-sources ""` swallows the next flag as its value - and '""' is the
    form that survives. subprocess passes an argument list, so the batch never hits this."""
    return " ".join("'\"\"'" if a == "" else subprocess.list2cmdline([a]) for a in cmd)


def extract_structured(payload: dict):
    """Pull the schema-checked object out of the CLI's result envelope."""
    for candidate in (payload.get("structured_output"), payload.get("result")):
        if isinstance(candidate, dict):
            inner = candidate.get("structured_output")
            if isinstance(inner, dict):
                return inner
            if "outcome" in candidate:
                return candidate
    return None


def kill_tree(pid: int) -> None:
    """Kill the applier and its children. A bare kill() leaves the MCP servers running, and a
    surviving one goes on driving the same Chrome the next offer is about to use."""
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                   capture_output=True, text=True)


def envelope_meta(payload: dict) -> dict:
    """The parts of the CLI's result envelope worth keeping, per launch.

    Raw numbers only - `stats.py` does every division. Three of these answer questions
    `total_cost_usd` cannot: `duration_api_ms` against the runner's wall clock says whether a
    slow offer was the model or the browser; the cache token counts say why an offer was
    expensive, since a cache read costs a tenth of a fresh input token; and `permission_denials`
    is the only place a tool the playbook wants but `--tools` withholds ever shows up.
    """
    meta = {}
    for k in ("session_id", "total_cost_usd", "num_turns", "is_error", "subtype",
              "duration_ms", "duration_api_ms", "ttft_ms", "time_to_request_ms",
              "stop_reason", "terminal_reason", "api_error_status", "queued_turn_count"):
        if payload.get(k) is not None:
            meta[k] = payload[k]

    usage = payload.get("usage") or {}
    if usage:
        meta["tokens"] = {
            "input": usage.get("input_tokens"),
            "output": usage.get("output_tokens"),
            "thinking": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
            "cache_read": usage.get("cache_read_input_tokens"),
            "cache_creation": usage.get("cache_creation_input_tokens"),
        }

    # One model per run today, but --model makes that a per-launch fact, so record which one
    # actually served the offer rather than which one was asked for.
    models = payload.get("modelUsage") or {}
    if models:
        meta["models"] = {
            (u.get("canonicalModel") or name): round(u.get("costUSD", 0.0), 6)
            for name, u in models.items()
        }

    denials = payload.get("permission_denials") or []
    if denials:
        meta["permission_denials"] = [d.get("tool_name", str(d)) if isinstance(d, dict) else str(d)
                                      for d in denials]
    return meta


def run_offer(offer: dict, mode: str, cmd: list, timeout: int):
    """Launch one applier. Returns (structured result or None, run-log metadata)."""
    prompt = PROMPT.format(
        mode=mode,
        offer=json.dumps(offer, ensure_ascii=False, indent=2),
        src=str(SRC),
    )
    env = dict(os.environ, CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")
    started = time.time()
    meta = {"url": offer.get("url"), "mode": mode}

    proc = subprocess.Popen(
        cmd, cwd=str(SRC), env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    try:
        out, err = proc.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc.pid)
        try:
            out, err = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            out, err = "", ""
        meta.update(exit_code=None, duration_s=round(time.time() - started, 1),
                    failure="timeout after {}s".format(timeout),
                    stderr_tail=(err or "")[-1500:])
        return None, meta
    except KeyboardInterrupt:
        kill_tree(proc.pid)
        raise

    meta["exit_code"] = proc.returncode
    meta["duration_s"] = round(time.time() - started, 1)

    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        meta["failure"] = "stdout was not JSON"
        meta["stdout_tail"] = (out or "")[-1500:]
        meta["stderr_tail"] = (err or "")[-1500:]
        return None, meta

    meta.update(envelope_meta(payload))

    result = extract_structured(payload)
    if result is None:
        meta["failure"] = "no structured_output in the result envelope"
        meta["stdout_tail"] = (out or "")[-1500:]
    return result, meta


# --------------------------------------------------------------------------- writing

def now_warsaw() -> str:
    try:
        from zoneinfo import ZoneInfo
        stamp = datetime.now(ZoneInfo("Europe/Warsaw"))
    except Exception:  # no tzdata on this box; the box itself runs on Warsaw time
        stamp = datetime.now().astimezone()
    return stamp.isoformat(timespec="seconds")


def log_line(offer: dict, result, meta: dict) -> dict:
    """One line for applications_log.jsonl. A dead applier still gets a line - a missing one
    means the next run applies to the offer twice."""
    if result is None:
        tail = (meta.get("stdout_tail") or meta.get("stderr_tail") or "").strip()
        line = {
            "url": offer.get("url", ""),
            "company": offer.get("company", ""),
            "title": offer.get("title", ""),
            "apply_type": "custom",
            "outcome": "blocked",
            "cv_used": "",
            "composed_answers": [],
            "blocked_reason": "applier-failure",
            "notes": "runner: {} (exit {}). {}".format(
                meta.get("failure", "applier returned nothing"),
                meta.get("exit_code"), tail[-600:]).strip(),
            "diagnostics": {"ats": "", "workarounds": [], "left_blank": []},
        }
    else:
        line = {k: result.get(k) for k in LOG_FIELDS}
        # The cockpit joins the log onto the offer list by url, so the worklist's url wins.
        if line.get("url") != offer.get("url"):
            meta["url_mismatch"] = line.get("url")
            line["url"] = offer.get("url", "")
        for k in ("company", "title"):
            if not line.get(k):
                line[k] = offer.get(k, "")

    return dict({"timestamp": now_warsaw()}, **{k: line.get(k) for k in LOG_FIELDS})


def append_log(line: dict) -> None:
    with LOG.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def append_todo(line: dict) -> None:
    note = " ".join((line.get("notes") or "").split())
    entry = ("- [ ] {} — {} — {}\n"
             "      reason: {}\n"
             "      note: {}\n").format(
        line.get("company"), line.get("title"), line.get("url"),
        line.get("blocked_reason"), note)
    with TODO.open("a", encoding="utf-8", newline="\n") as f:
        f.write(entry)


def archive_transcript(session_id):
    """Copy one run's trace out of the CLI's folder, which is swept 30 days after last
    activity. The run log says an offer cost $1.33 and survives forever; the trace saying
    why - every tool call, every tool error, the gaps between steps - does not. Copied raw:
    the screenshots are most of the bytes and no metric reads them today, but they are the
    only record of what the applier actually saw. Returns the copy, or None."""
    if not session_id:
        return None
    src = PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", str(SRC)) / (session_id + ".jsonl")
    if not src.exists():
        # A run launched from another cwd still counts.
        src = next(PROJECTS.glob("*/" + session_id + ".jsonl"), None)
        if src is None:
            return None
    try:
        TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
        dest = TRANSCRIPTS / src.name
        shutil.copy2(src, dest)
    except OSError:
        # An unreadable trace is a lost diagnostic, never a lost application: the log line
        # is already on disk by now, and the batch has more offers to get through.
        return None
    return dest


def append_run_log(meta: dict) -> None:
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOG.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(dict({"timestamp": now_warsaw()}, **meta),
                           ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- selection

def parse_pick(spec: str, total: int) -> list:
    """`--pick 1`, `--pick 3-5`, `--pick 2,4` -> zero-based indexes, in worklist order."""
    picked = []
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part[1:]:
            a, b = part.split("-", 1)
            rng = range(int(a), int(b) + 1)
        else:
            rng = [int(part)]
        for n in rng:
            if not 1 <= n <= total:
                sys.exit("--pick {}: worklist has {} offers".format(n, total))
            if n - 1 not in picked:
                picked.append(n - 1)
    return picked


# --------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="Apply to every offer in runner/data/worklist.json.")
    ap.add_argument("--mode", choices=["review", "auto"], default="review",
                    help="review (default): fill, stop before Submit. auto: fill and submit.")
    ap.add_argument("--limit", type=int, default=None, help="process at most N offers")
    ap.add_argument("--pick", default=None, metavar="SPEC",
                    help="which offers, 1-based worklist positions: 1 | 3-5 | 2,4")
    ap.add_argument("--model", default="sonnet", help="applier model (default sonnet)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and the exact command, launch nothing")
    ap.add_argument("--no-autoclick", action="store_true",
                    help="do not answer the browser's site-permission card; a new employer "
                         "domain then waits for you to click it")
    ap.add_argument("--timeout", type=int, default=900, help="seconds per offer (default 900)")
    args = ap.parse_args()

    if not WORKLIST.exists():
        return fail("runner/data/worklist.json is missing - pick offers in the finder cockpit "
                    "(python finder\\app.py) and hit 'Write worklist'.")
    offers = json.loads(WORKLIST.read_text(encoding="utf-8"))
    if not offers:
        return fail("runner/data/worklist.json is empty - pick offers in the finder cockpit.")

    if args.pick:
        offers = [offers[i] for i in parse_pick(args.pick, len(offers))]
    if args.limit:
        offers = offers[:args.limit]

    for path in (MCP_CONFIG, SCHEMA):
        if not path.exists():
            return fail("missing {}".format(path))
    schema_text = json.dumps(json.loads(SCHEMA.read_text(encoding="utf-8")),
                             ensure_ascii=False, separators=(",", ":"))
    cmd = build_cmd(schema_text, args.model)

    print("model    {}".format(args.model))
    print("mode     {}".format(args.mode))
    print("offers   {}".format(len(offers)))

    if args.dry_run:
        print("\ncommand (prompt goes on stdin, cwd = src):")
        print("  " + ps_cmdline(cmd[:-1] + ["<schema>"]))
        print("\nqueue:")
        for i, o in enumerate(offers, 1):
            print("  {:>2}. {} - {}".format(i, o.get("company"), o.get("title")))
        return 0

    if not ensure_chrome():
        return fail("CDP port 9222 never answered - start Chrome by hand:\n"
                    "  powershell -File tools\\mcp_webfile\\start_chrome.ps1")

    autoclick = None if args.no_autoclick else start_autoclick()
    rows, metas = [], []
    try:
        for i, offer in enumerate(offers, 1):
            print("\n[{}/{}] {} - {}".format(i, len(offers),
                                             offer.get("company"), offer.get("title")))
            result, meta = run_offer(offer, args.mode, cmd, args.timeout)
            line = log_line(offer, result, meta)
            append_log(line)
            if line["outcome"] == "blocked":
                append_todo(line)
            meta["outcome"] = line["outcome"]
            meta["blocked_reason"] = line["blocked_reason"]
            append_run_log(meta)
            if not archive_transcript(meta.get("session_id")):
                print("      ! no transcript archived - stats.py loses this run in 30 days")
            rows.append(line)
            metas.append(meta)
            flag = "" if result else "   <- applier failure, logged as blocked"
            print("      {}  ({}s){}".format(line["outcome"], meta["duration_s"], flag))
    finally:
        # Standing consent to open any domain lasts exactly as long as the batch, Ctrl-C
        # and a crash included.
        if autoclick:
            kill_tree(autoclick.pid)

    summary(rows, metas, args.mode)
    return 0


def summary(rows: list, metas: list, mode: str) -> None:
    print("\n" + "=" * 78)
    width = max([len(r.get("company") or "") for r in rows] or [7])
    for r in rows:
        note = " ".join((r.get("notes") or "").split())[:70]
        print("  {:<{w}}  {:<13}  {:<16}  {}".format(
            r.get("company") or "", r.get("apply_type") or "", r.get("outcome") or "",
            note, w=width))

    counts = {}
    for r in rows:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    print("\n  " + "  ".join("{}: {}".format(k, v) for k, v in sorted(counts.items())))

    cost = sum(m.get("total_cost_usd") or 0.0 for m in metas)
    wall = sum(m.get("duration_s") or 0.0 for m in metas)
    api = sum(m.get("duration_api_ms") or 0 for m in metas) / 1000.0
    print("  ${:.2f} total, ${:.2f}/offer   {:.0f}s wall, {:.0f}s of it the model"
          .format(cost, cost / max(len(metas), 1), wall, api))

    blocked = [r for r in rows if r["outcome"] == "blocked"]
    if blocked:
        print("\n  {} blocked -> runner\\data\\todo_manual.md:".format(len(blocked)))
        for r in blocked:
            print("    {}: {}".format(r.get("company"), r.get("blocked_reason")))
    if mode == "review":
        print("\n  review mode: every application is STAGED, not submitted. "
              "Click Submit yourself in Chrome.")
    print("  log      runner\\data\\applications_log.jsonl (+{} lines)".format(len(rows)))
    print("  run log  runner\\data\\run_log.jsonl")


def fail(msg: str) -> int:
    print("error: {}".format(msg), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
