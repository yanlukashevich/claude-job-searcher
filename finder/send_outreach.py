"""Send the emails in an outreach file (finder/data/outreach_*.md) through Gmail SMTP.

The Gmail connector can only attach a file passed inline as base64, which no model can copy
out of a PDF reliably. So the sending happens here: Python reads the CV from disk and
attaches it byte for byte.

An outreach file is a preamble with a "Before sending" checklist, then one `## N. Company —
Title` section per email carrying `**To:**`, `**Subject:**`, `**Attach:**` (a path relative to
the repo root) and the body in the first ``` fence.

  - Dry run by default: prints every email and checks its attachment. `--send` sends.
  - An unchecked `- [ ]` item that names a section's company holds that section back
    (e.g. "Soneta is STAGED, not submitted" -- its email says you already applied).
    Tick the box in the file once it is true.
  - Every sent email is appended to finder/data/outreach_sent.jsonl the moment it leaves, and
    a (file, recipient) pair already there is never sent again -- so a run that dies halfway
    can simply be run again.

Credentials, needed only with --send (use an App Password, not your Google password:
myaccount.google.com -> Security -> 2-Step Verification -> App passwords):
  $env:GMAIL_APP_PASSWORD = "abcd efgh ijkl mnop"
  $env:GMAIL_ADDRESS      = "you@gmail.com"      # optional, defaults to SENDER below

Usage:
  python finder/send_outreach.py finder/data/outreach_2026-09-10.md              # dry run
  python finder/send_outreach.py finder/data/outreach_2026-09-10.md --send
  python finder/send_outreach.py finder/data/outreach_2026-09-10.md --send --only 2,3
"""
import argparse
import datetime
import os
import re
import smtplib
import sys
import time
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

from common import DATA, ROOT, append_jsonl, read_jsonl

SENDER = "yanlukashevich2@gmail.com"
SENDER_NAME = "Yan Lukashevich"
SENT_LOG = DATA / "outreach_sent.jsonl"
PAUSE_S = 3                       # between sends; a burst of mail reads as a bot

SECTION = re.compile(r"^## (\d+)\. (.+?) — (.+)$", re.M)
UNCHECKED = re.compile(r"^- \[ \] (.+)$", re.M)


def parse(path):
    """Outreach file -> (unchecked checklist items, [email dict per section])."""
    text = path.read_text(encoding="utf-8")
    heads = list(SECTION.finditer(text))
    if not heads:
        sys.exit(f"FATAL: no '## N. Company — Title' sections in {path.name}.")
    todo = UNCHECKED.findall(text[:heads[0].start()])

    emails = []
    for i, h in enumerate(heads):
        body_end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        sec = text[h.end():body_end]

        def field(name):
            m = re.search(rf"\*\*{name}:\*\* (.+)", sec)
            if not m:
                sys.exit(f"FATAL: section {h.group(1)} ({h.group(2)}) has no **{name}:** line.")
            return m.group(1).strip()

        fence = re.search(r"```\n(.*?)\n```", sec, re.S)
        if not fence:
            sys.exit(f"FATAL: section {h.group(1)} ({h.group(2)}) has no ``` body.")
        emails.append({
            "n": int(h.group(1)),
            "company": h.group(2).strip(),
            "to": field("To"),
            "subject": field("Subject"),
            "attach": ROOT / field("Attach").strip("`"),
            "body": unwrap(fence.group(1)),
        })
    return todo, emails


def unwrap(body):
    """Join each paragraph's hard-wrapped lines, so the recipient's client does the wrapping.

    The drafts are wrapped at ~72 columns for reading in an editor; sent as-is, every line
    would break early. The last paragraph is the signature, whose line breaks are meant.
    """
    paras = body.strip().split("\n\n")
    return "\n\n".join([" ".join(l.strip() for l in p.splitlines()) for p in paras[:-1]]
                       + [paras[-1]])


def held_by(email, todo):
    """The unchecked checklist item that names this email's company, if any."""
    name = email["company"].split()[0].lower()
    return next((t for t in todo if name in t.lower()), None)


def build(email, sender):
    msg = EmailMessage()
    msg["From"] = formataddr((SENDER_NAME, sender))
    msg["To"] = email["to"]
    msg["Subject"] = email["subject"]
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[1])
    msg.set_content(email["body"])
    msg.add_attachment(email["attach"].read_bytes(), maintype="application", subtype="pdf",
                       filename=email["attach"].name)
    return msg


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file", type=Path, help="the outreach_*.md file")
    ap.add_argument("--send", action="store_true", help="actually send (default: dry run)")
    ap.add_argument("--only", help="comma-separated section numbers, e.g. 2,3")
    args = ap.parse_args()

    todo, emails = parse(args.file)
    if args.only:
        wanted = {int(n) for n in args.only.split(",")}
        emails = [e for e in emails if e["n"] in wanted]

    sent = {(r["file"], r["to"]) for r in read_jsonl(SENT_LOG)}
    ready = []
    for e in emails:
        print(f"\n=== {e['n']}. {e['company']}  ->  {e['to']}")
        print(f"Subject: {e['subject']}")
        print(f"Attach:  {e['attach'].relative_to(ROOT)}"
              + ("" if e["attach"].is_file() else "   <-- MISSING"))
        print("-" * 72 + "\n" + e["body"] + "\n" + "-" * 72)
        if (args.file.name, e["to"]) in sent:
            print("SKIP: already sent (outreach_sent.jsonl)")
        elif not e["attach"].is_file():
            print("SKIP: attachment not found")
        elif reason := held_by(e, todo):
            print(f"HELD: unchecked in the file -> {reason}")
        else:
            ready.append(e)

    other = [t for t in todo if not any(held_by(e, [t]) for e in emails)]
    for t in other:
        print(f"\nnote: unchecked checklist item -> {t}")
    print(f"\n{len(ready)} of {len(emails)} ready to send.")

    if not args.send:
        print("Dry run. Add --send to send them.")
        return 0
    if not ready:
        return 0

    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    if not password:
        sys.exit("FATAL: set GMAIL_APP_PASSWORD first (see the top of this file).")
    sender = os.environ.get("GMAIL_ADDRESS", SENDER)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as smtp:
        try:
            smtp.login(sender, password)
        except smtplib.SMTPAuthenticationError:
            sys.exit("FATAL: Gmail refused the login. Is it an App Password, for " + sender + "?")
        for i, e in enumerate(ready):
            if i:
                time.sleep(PAUSE_S)
            msg = build(e, sender)
            smtp.send_message(msg)
            # Logged per email, straight away: the log is what stops a re-run double-sending.
            append_jsonl(SENT_LOG, [{
                "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                "file": args.file.name, "n": e["n"], "company": e["company"],
                "to": e["to"], "subject": e["subject"],
                "attachment": str(e["attach"].relative_to(ROOT)),
                "message_id": msg["Message-ID"],
            }])
            print(f"SENT {e['n']}. {e['company']} -> {e['to']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
