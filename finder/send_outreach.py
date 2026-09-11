"""Send the approved outreach cards in finder/data/dig_deeper.json through Gmail SMTP.

The Gmail connector can only attach a file passed inline as base64, which no model can copy
out of a PDF reliably. So the sending happens here: Python reads the CV from disk and
attaches it byte for byte.

A card goes out only when it is READY: it has an email, a subject, a body and a CV on disk; you
clicked OK to send on /outreach and nothing changed since (the stored stamp still matches); its
offer's application actually went out (the drafts say "I already applied"); and this offer +
address pair is not in the sent log already. The body is sent exactly as stored.

  - Dry run by default: says READY or why not for every card. `--send` sends.
  - At most --max emails per run, with a random --pause between them. A burst of mail reads as
    a bot, and Gmail drops an SMTP connection left idle that long, so each email logs in anew.
  - Each email that leaves is logged to finder/data/outreach_sent.jsonl with its full text,
    then its card is removed from dig_deeper.json -- like the apply queue, an offer leaves the
    list once it is logged. A run that dies in between just finishes the removal next time.
  - `--test-to ADDRESS` sends the real email to you instead: it skips the approval and the
    application checks (nothing reaches the employer), and logs and removes nothing.
  - `--url URL` (repeatable) limits the run to those cards, sent in that order. The /outreach
    page's Send button passes the cards you confirmed, so what you saw is what goes.

Credentials, needed only with --send (use an App Password, not your Google password:
myaccount.google.com -> Security -> 2-Step Verification -> App passwords):
  $env:GMAIL_APP_PASSWORD = "abcd efgh ijkl mnop"      # this shell only, or once for good:
  [Environment]::SetEnvironmentVariable("GMAIL_APP_PASSWORD", "abcd efgh ijkl mnop", "User")
  $env:GMAIL_ADDRESS      = "you@gmail.com"            # optional, defaults to SENDER below
The user-level one is read straight from the registry, so a shell or app.py started before you
set it -- the /outreach page's Send button runs inside app.py -- still finds it.

Usage:
  python finder/send_outreach.py                                     # dry run
  python finder/send_outreach.py --send                              # up to 5, 2-5 min apart
  python finder/send_outreach.py --send --test-to you@gmail.com --max 1 --only soneta
"""
import argparse
import datetime
import os
import random
import smtplib
import sys
import time
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

import outreach
from common import ROOT, append_jsonl

SENDER = "yanlukashevich2@gmail.com"
SENDER_NAME = "Yan Lukashevich"


def password():
    """The Gmail App Password, spaces dropped, or ''. The process env first, then (Windows) the
    user-level variable from the registry, which a process started before it was set lacks."""
    pw = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not pw and sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                pw = winreg.QueryValueEx(k, "GMAIL_APP_PASSWORD")[0]
        except OSError:
            pw = ""
    return pw.replace(" ", "")


def verdict(card, ctx, test):
    """(ready, why-not). The one place the send rules are applied, before and after a pause."""
    st = outreach.status(card, ctx)
    if not outreach.has_draft(card):
        return False, "no draft yet" + ("" if st["has_contacts"] else " (no contact either)")
    if st["problems"]:
        return False, "; ".join(st["problems"])
    if test:
        return True, "READY (test)"
    if st["sent_at"]:
        return False, f"already sent {st['sent_at'][:16]}"
    if st["approval_stale"]:
        return False, "approval is stale — draft changed"
    if not st["approved_ok"]:
        return False, "not approved"
    if st["held"]:
        return False, "HELD: " + st["held"]
    return True, "READY"


def build(card, cv, sender, to):
    msg = EmailMessage()
    msg["From"] = formataddr((SENDER_NAME, sender))
    msg["To"] = to
    subject = outreach.text(card["subject"]).strip()
    if to != card["email"].strip():
        subject = f"[test → {card['email'].strip()}] {subject}"
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[1])
    msg.set_content(outreach.text(card["body"]))
    path = ROOT / cv
    msg.add_attachment(path.read_bytes(), maintype="application", subtype="pdf",
                       filename=path.name)
    return msg


def send(msg, sender, password):
    """One login per email: the pauses are minutes long, and Gmail drops an idle connection."""
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)


def log_line(card, cv, msg):
    """The whole card, minus the approval stamp, plus what left. The card itself is about to
    be removed, so this line is the only record /history has of it."""
    line = {"ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "url": card["url"], "company": card.get("company", ""),
            "title": card.get("title", ""), "to": card["email"].strip(),
            "subject": outreach.text(card["subject"]).strip(),
            "body": outreach.text(card["body"]), "attachment": cv,
            "message_id": msg["Message-ID"], "other": card.get("other", ""),
            "note": card.get("note", "")}
    line.update({k: v for k, v in card.items()
                 if k not in line and k not in ("email", "cv", "approved")})
    return line


def pause_range(s):
    lo, _, hi = s.partition("-")
    lo, hi = int(lo), int(hi or lo)
    if not 0 <= lo <= hi:
        raise argparse.ArgumentTypeError("--pause wants MIN-MAX seconds, e.g. 120-300")
    return lo, hi


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--send", action="store_true", help="actually send (default: dry run)")
    ap.add_argument("--max", type=int, default=5, help="emails per run (default 5)")
    ap.add_argument("--pause", type=pause_range, default=(120, 300),
                    help="random seconds between emails, MIN-MAX (default 120-300)")
    ap.add_argument("--test-to", metavar="ADDRESS",
                    help="send to this address instead; no approval needed, nothing logged")
    ap.add_argument("--only", metavar="TEXT",
                    help="only cards whose company, title or url contains TEXT")
    ap.add_argument("--url", action="append", metavar="URL",
                    help="only this card (repeatable); sent in the order given")
    args = ap.parse_args()

    try:
        cards = outreach.load()
    except outreach.CardsError as e:
        sys.exit(f"FATAL: {e}")
    ctx = outreach.Context()
    test = bool(args.test_to)

    picked = list(cards.values())
    if args.url:
        picked = [cards[u] for u in dict.fromkeys(args.url) if u in cards]
        if len(picked) < len(set(args.url)):
            print(f"{len(set(args.url)) - len(picked)} of the given card(s) are no longer "
                  "on the list.")

    ready, finish = [], []
    for card in picked:
        hay = " ".join(str(card.get(k, "")) for k in ("company", "title", "url")).lower()
        if args.only and args.only.lower() not in hay:
            continue
        ok, why = verdict(card, ctx, test)
        cv = outreach.cv_of(card, ctx)
        print(f"\n=== {card.get('company', '?')} — {card.get('title', '?')}")
        if outreach.has_draft(card):
            print(f"    to {card.get('email') or '?'} · CV {cv or '?'}")
        print(f"    {why}")
        if ok:
            ready.append(card)
            print(f"    Subject: {outreach.text(card['subject']).strip()}")
            print("    " + "-" * 68)
            print("\n".join("    " + line for line in outreach.text(card["body"]).splitlines()))
            print("    " + "-" * 68)
        elif why.startswith("already sent"):
            finish.append(card)

    print(f"\n{len(ready)} of {len(picked)} cards ready"
          + (f"; sending the first {args.max}" if len(ready) > args.max else "") + ".")
    if not args.send:
        if finish:
            print(f"{len(finish)} already-sent card(s) will be removed from the list on --send.")
        print("Dry run. Add --send to send.")
        return 0

    # A card already in the sent log was mailed by a run that died before removing it.
    for card in finish:
        outreach.remove(ctx.urls(card))
        print(f"removed already-sent card: {card.get('company')}")
    ready = ready[:args.max]
    if not ready:
        return 0

    pw = password()
    if not pw:
        sys.exit("FATAL: set GMAIL_APP_PASSWORD first (see the top of this file).")
    sender = os.environ.get("GMAIL_ADDRESS", SENDER)

    for i, card in enumerate(ready):
        if i:
            wait = random.randint(*args.pause)
            print(f"next in {wait // 60}m{wait % 60:02d}s ...", flush=True)
            time.sleep(wait)
            # Minutes have passed: you or an agent may have edited this card, which voids
            # the approval. Judge the card as it is on disk now, not as it was loaded.
            try:
                card = outreach.load().get(card["url"])
            except outreach.CardsError as e:
                sys.exit(f"FATAL: {e}")
            ctx = outreach.Context()
            ok, why = verdict(card, ctx, test) if card else (False, "card removed")
            if not ok:
                print(f"SKIP {card.get('company') if card else ''}: changed meanwhile -> {why}")
                continue
        cv = outreach.cv_of(card, ctx)
        to = args.test_to or card["email"].strip()
        msg = build(card, cv, sender, to)
        try:
            send(msg, sender, pw)
        except smtplib.SMTPAuthenticationError:
            sys.exit("FATAL: Gmail refused the login. Is it an App Password, for " + sender + "?")
        except (smtplib.SMTPException, OSError) as e:
            sys.exit(f"FATAL: sending to {to} failed, stopping: {e}")
        if test:
            print(f"SENT (test) {card.get('company')} -> {to}")
            continue
        # Log first, then remove: a line with no card is finished by the next run, a removed
        # card with no line would be an email nobody can see was sent.
        append_jsonl(outreach.SENT_LOG, [log_line(card, cv, msg)])
        outreach.remove(ctx.urls(card))
        print(f"SENT {card.get('company')} -> {to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
