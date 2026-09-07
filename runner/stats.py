#!/usr/bin/env python
"""Report on past applier runs: `runner/data/run_log.jsonl` joined to the CLI transcripts.

    python runner\\stats.py                 # last 20 launches, table + aggregates + warnings
    python runner\\stats.py --last 100
    python runner\\stats.py --offer contro  # one run in full: every tool call, every error
    python runner\\stats.py --json          # the same rows, machine-readable

`run_batch.py` records what the result envelope reports (cost, tokens, wall clock, API time).
That says an offer cost $1.33; it never says why. The why is in the transcript `run_batch.py`
archived to `runner/data/transcripts/<session_id>.jsonl` - every tool call, every tool error,
the gaps between steps - and `session_id` in the run log is the key to it. Nothing here costs
a token or asks the applier for anything; it is all read back off disk.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
RUN_LOG = ROOT / "runner" / "data" / "run_log.jsonl"
APPLICATIONS = ROOT / "runner" / "data" / "applications_log.jsonl"
ARCHIVE = ROOT / "runner" / "data" / "transcripts"
PROJECTS = Path.home() / ".claude" / "projects"

CONTEXT_WINDOW = 200_000

# Company names carry Polish diacritics and the Windows console defaults to cp1250.
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Every offer is meant to open exactly one of these - the whole reason they are separate files.
QUIRKS = {"portal_quirks.md", "ats_quirks.md"}


# --------------------------------------------------------------------------- transcripts

def transcript_path(session_id: str):
    """The archive first: `run_batch.py` copies every trace there because the CLI deletes its
    own 30 days after last activity, taking half of this report with it. Then the CLI's own
    folder, named after the agent's cwd with every non-alphanumeric run to a dash - a run from
    before the archive existed is still readable until the sweep reaches it. Then a search, for
    a run launched from elsewhere."""
    kept = ARCHIVE / (session_id + ".jsonl")
    if kept.exists():
        return kept
    guess = PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", str(SRC)) / (session_id + ".jsonl")
    if guess.exists():
        return guess
    for found in PROJECTS.glob("*/" + session_id + ".jsonl"):
        return found
    return None


_TRANSCRIPTS = {}   # path -> parsed. A finished run's transcript is immutable, so the
                    # cockpit can ask for the same one on every click for free.


def read_transcript(path: Path) -> dict:
    """Everything worth knowing about one applier run, from its trace."""
    tools, actions, reads = Counter(), Counter(), []
    errors, stamps = [], []
    peak_ctx = 0
    version = model = effort = None
    pending = {}   # tool_use_id -> name, so an error can name the tool that raised it

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            line = json.loads(raw)
        except json.JSONDecodeError:
            continue

        stamp = line.get("timestamp")
        if stamp:
            stamps.append(stamp)

        if line.get("type") == "assistant":
            version = line.get("version") or version
            effort = line.get("effort") or effort
            msg = line.get("message") or {}
            model = msg.get("model") or model
            usage = msg.get("usage") or {}
            peak_ctx = max(peak_ctx, (usage.get("input_tokens") or 0)
                           + (usage.get("cache_read_input_tokens") or 0)
                           + (usage.get("cache_creation_input_tokens") or 0))
            for block in msg.get("content") or []:
                if block.get("type") != "tool_use":
                    continue
                name = block.get("name", "?")
                tools[name] += 1
                pending[block.get("id")] = name
                args = block.get("input") if isinstance(block.get("input"), dict) else {}
                if name == "mcp__chrome__computer":
                    actions[args.get("action", "?")] += 1
                elif name == "Read":
                    reads.append(Path(str(args.get("file_path", ""))).name)

        elif line.get("type") == "user":
            content = (line.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if block.get("type") == "tool_result" and block.get("is_error"):
                    text = block.get("content")
                    if isinstance(text, list):
                        text = " ".join(str(p.get("text", "")) for p in text
                                        if isinstance(p, dict))
                    errors.append({"tool": pending.get(block.get("tool_use_id"), "?"),
                                   "message": " ".join(str(text).split())[:200]})

    times = sorted(datetime.fromisoformat(s.replace("Z", "+00:00")) for s in stamps)
    gaps = [round((b - a).total_seconds(), 1) for a, b in zip(times, times[1:])]
    return {
        "tools": dict(tools.most_common()),
        "tool_calls": sum(tools.values()),
        "computer_actions": dict(actions.most_common()),
        "screenshots": actions.get("screenshot", 0),
        "reads": reads,
        "quirks_read": sorted(QUIRKS.intersection(reads)),
        "cv_attached": tools.get("mcp__webfile__attach_file", 0) > 0,
        "tool_errors": len(errors),
        "errors": errors,
        "peak_context": peak_ctx,
        "longest_gap_s": max(gaps) if gaps else 0.0,
        "transcript_mb": round(path.stat().st_size / 1e6, 1),
        "cli_version": version,
        "model": model,
        "effort": effort,
    }


# --------------------------------------------------------------------------- joining

def read_runs() -> list:
    if not RUN_LOG.exists():
        return []
    return [json.loads(l) for l in RUN_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_runs(last: int) -> list:
    runs = read_runs()
    if not runs:
        sys.exit("no {} yet - run a batch first".format(RUN_LOG))
    return runs[-last:] if last else runs


def load_applications() -> dict:
    """url -> the most recent application line, for apply_type and the ATS vendor. The run log
    knows what a launch cost; only the audit trail knows what kind of form it was."""
    by_url = {}
    if APPLICATIONS.exists():
        for raw in APPLICATIONS.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            try:
                line = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if line.get("url"):
                by_url[line["url"]] = line
    return by_url


def portal(url: str) -> str:
    if "justjoin" in (url or ""):
        return "justjoin"
    if "pracuj" in (url or ""):
        return "pracuj"
    return "other"


def enrich(run: dict, applications: dict) -> dict:
    row = dict(run)
    row["portal"] = portal(run.get("url", ""))
    app = applications.get(run.get("url"))
    if app:
        row["apply_type"] = app.get("apply_type")
        row["company"] = app.get("company")
        row["ats"] = (app.get("diagnostics") or {}).get("ats") or ""

    wall = run.get("duration_s") or 0.0
    api = (run.get("duration_api_ms") or 0) / 1000.0
    row["api_s"] = round(api, 1)
    row["api_share"] = round(api / wall, 3) if wall and api else None

    tokens = run.get("tokens") or {}
    fresh = (tokens.get("input") or 0) + (tokens.get("cache_creation") or 0)
    cached = tokens.get("cache_read") or 0
    row["cache_hit"] = round(cached / (cached + fresh), 3) if (cached + fresh) else None

    sid = run.get("session_id")
    path = transcript_path(sid) if sid else None
    row["transcript"] = str(path) if path else None
    if path:
        key = str(path)
        if key not in _TRANSCRIPTS:
            _TRANSCRIPTS[key] = read_transcript(path)
        row.update(_TRANSCRIPTS[key])
    return row


# --------------------------------------------------------------------------- output

def pct(value):
    return "  -  " if value is None else "{:>4.0f}%".format(100 * value)


def table(rows: list) -> None:
    head = ("  #  company            outcome         cost   wall   api%  cache  turns  tools"
            "  shots   err   ctx")
    print(head)
    print("  " + "-" * (len(head) - 2))
    for i, r in enumerate(rows, 1):
        print("{:>3}  {:<18.18} {:<14.14} {:>6} {:>5}s {} {} {:>6} {:>6} {:>6} {:>5} {:>5}".format(
            i,
            r.get("company") or portal(r.get("url", "")),
            (r.get("outcome") or "?") + ("!" if r.get("is_error") else ""),
            "${:.2f}".format(r["total_cost_usd"]) if r.get("total_cost_usd") else "-",
            int(r.get("duration_s") or 0),
            pct(r.get("api_share")),
            pct(r.get("cache_hit")),
            r.get("num_turns", "-"),
            r.get("tool_calls", "-"),
            r.get("screenshots", "-"),
            r.get("tool_errors", "-"),
            "{}k".format(round((r.get("peak_context") or 0) / 1000)) if r.get("peak_context")
            else "-",
        ))


def group(rows: list, key: str) -> None:
    buckets = {}
    for r in rows:
        name = r.get(key) or "?"
        b = buckets.setdefault(name, {"n": 0, "cost": 0.0, "wall": 0.0, "shots": 0, "err": 0})
        b["n"] += 1
        b["cost"] += r.get("total_cost_usd") or 0.0
        b["wall"] += r.get("duration_s") or 0.0
        b["shots"] += r.get("screenshots") or 0
        b["err"] += r.get("tool_errors") or 0
    print("\n  by {}:".format(key))
    for name, b in sorted(buckets.items(), key=lambda kv: -kv[1]["cost"]):
        print("    {:<16.16} {:>3} runs  ${:.2f} total  ${:.2f}/offer  {:>4.0f}s/offer"
              "  {:.1f} shots  {:.1f} errors".format(
                  name, b["n"], b["cost"], b["cost"] / b["n"], b["wall"] / b["n"],
                  b["shots"] / b["n"], b["err"] / b["n"]))


def aggregates(rows: list) -> None:
    cost = sum(r.get("total_cost_usd") or 0.0 for r in rows)
    wall = sum(r.get("duration_s") or 0.0 for r in rows)
    api = sum(r.get("api_s") or 0.0 for r in rows)
    shots = sum(r.get("screenshots") or 0 for r in rows)
    print("\n  {} launches  ${:.2f}  ${:.2f}/offer  {:.0f}s/offer".format(
        len(rows), cost, cost / len(rows), wall / len(rows)))
    if wall and api:
        # On a run of a few seconds the envelope's API time can exceed the wall clock, so the
        # Chrome half is only meaningful when it is actually positive.
        share = api / wall
        print("  {:.0f}% of the wall clock was the model{}".format(
            100 * share,
            "; the other {:.0f}% was Chrome".format(100 * (1 - share)) if share < 1 else ""))
    if shots:
        priced = [r for r in rows if r.get("total_cost_usd") and r.get("screenshots")]
        tail = ""
        if priced:
            tail = "  (~${:.3f} per screenshot)".format(
                sum(r["total_cost_usd"] for r in priced)
                / sum(r["screenshots"] for r in priced))
        print("  {} screenshots, {:.1f} per offer{}".format(shots, shots / len(rows), tail))

    for key in ("outcome", "portal", "apply_type", "ats", "model"):
        if any(r.get(key) for r in rows):
            group(rows, key)


def row_warnings(r: dict) -> list:
    """What is wrong with one run. No offer name in front - the cockpit shows these under the
    offer they belong to; the CLI puts the name back on because its list mixes offers."""
    out = []
    if len(r.get("quirks_read") or []) > 1:
        out.append("read both quirks files ({}) - the split exists so each offer "
                   "opens one".format(", ".join(r["quirks_read"])))
    if r.get("permission_denials"):
        out.append("tool denied by --tools: {}".format(", ".join(r["permission_denials"])))
    if r.get("tool_errors"):
        out.append("{} tool errors, first: {} - {}".format(
            r["tool_errors"], r["errors"][0]["tool"], r["errors"][0]["message"][:90]))
    if (r.get("peak_context") or 0) > 0.6 * CONTEXT_WINDOW:
        out.append("peak context {}k of {}k".format(
            round(r["peak_context"] / 1000), CONTEXT_WINDOW // 1000))
    if r.get("subtype") == "error_max_turns" or r.get("stop_reason") == "max_tokens":
        out.append("hit a limit ({})".format(r.get("subtype") or r.get("stop_reason")))
    if r.get("session_id") and not r.get("transcript"):
        out.append("transcript gone (session {})".format(r["session_id"][:8]))
    if r.get("cv_attached") is False and (r.get("outcome") or "").startswith("applied"):
        out.append("logged as applied but attach_file was never called")
    return out


def warnings(rows: list) -> None:
    out = ["{}: {}".format(r.get("company") or r.get("url", "")[:48], w)
           for r in rows for w in row_warnings(r)]
    if out:
        print("\n  warnings")
        for w in out:
            print("    ! " + w)


def detail(row: dict) -> None:
    print("\n{} - {}".format(row.get("company") or "?", row.get("url")))
    print("  {}  {}  {}".format(row.get("outcome"), row.get("mode"), row.get("timestamp", "")))
    print("  ${:.4f}   {}s wall, {}s model ({})   {} turns   cache {}".format(
        row.get("total_cost_usd") or 0.0, row.get("duration_s"), row.get("api_s"),
        pct(row.get("api_share")).strip(), row.get("num_turns"),
        pct(row.get("cache_hit")).strip()))
    tokens = row.get("tokens") or {}
    if tokens:
        print("  tokens   in {} / out {} (thinking {}) / cache read {} / cache write {}".format(
            *(tokens.get(k) for k in ("input", "output", "thinking",
                                      "cache_read", "cache_creation"))))
    print("  model    {}  effort {}  cli {}".format(
        row.get("model"), row.get("effort"), row.get("cli_version")))
    if not row.get("transcript"):
        print("  (no transcript on disk - nothing below)")
        return
    print("  peak ctx {}k   longest gap between steps {}s   transcript {}MB".format(
        round((row.get("peak_context") or 0) / 1000), row.get("longest_gap_s"),
        row.get("transcript_mb")))
    print("  files    {}".format(", ".join(row.get("reads") or []) or "none"))
    print("  cv       {}".format("attached" if row.get("cv_attached") else "NOT attached"))
    print("\n  tool calls ({} total)".format(row.get("tool_calls")))
    for name, n in (row.get("tools") or {}).items():
        print("    {:<34} {}".format(name, n))
    if row.get("computer_actions"):
        print("  computer actions: " + ", ".join(
            "{} x{}".format(k, v) for k, v in row["computer_actions"].items()))
    if row.get("errors"):
        print("\n  tool errors ({})".format(row["tool_errors"]))
        for e in row["errors"]:
            print("    ! {}: {}".format(e["tool"], e["message"]))


def seconds_between(a: str, b: str) -> float:
    try:
        return abs((datetime.fromisoformat((a or "").replace("Z", "+00:00"))
                    - datetime.fromisoformat((b or "").replace("Z", "+00:00"))).total_seconds())
    except (AttributeError, ValueError):
        return float("inf")


def run_for(url: str, at: str = ""):
    """The run behind one application-log line, enriched and with its warnings, or None.

    A url can be launched more than once (a retry, a re-post), so the timestamp picks the
    attempt. The runner writes both logs from the same loop iteration seconds apart, which is
    the join: there is no run id in the audit trail, and adding one would only restate what the
    pair of timestamps already says. Nothing matches within five minutes -> no run (most of the
    log predates run_log.jsonl entirely).
    """
    hits = [r for r in read_runs() if r.get("url") == url]
    if not hits:
        return None
    if at:
        hits.sort(key=lambda r: seconds_between(r.get("timestamp"), at))
        if seconds_between(hits[0].get("timestamp"), at) > 300:
            return None
    row = enrich(hits[0] if at else hits[-1], load_applications())
    row["warnings"] = row_warnings(row)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--last", type=int, default=20, help="how many launches (default 20, 0=all)")
    ap.add_argument("--offer", metavar="TEXT",
                    help="show one run in full: substring of the url or company")
    ap.add_argument("--json", action="store_true", help="dump the joined rows and exit")
    args = ap.parse_args()

    applications = load_applications()
    rows = [enrich(r, applications) for r in load_runs(args.last)]

    if args.offer:
        needle = args.offer.lower()
        hits = [r for r in rows
                if needle in (r.get("url") or "").lower()
                or needle in (r.get("company") or "").lower()]
        if not hits:
            return fail("no run matches {!r} in the last {} launches".format(
                args.offer, len(rows)))
        for row in hits:
            detail(row)
        return 0

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    table(rows)
    aggregates(rows)
    warnings(rows)
    print("\n  one run in full:  python runner\\stats.py --offer <company>")
    return 0


def fail(msg: str) -> int:
    print("error: " + msg, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
