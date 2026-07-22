# Manual TODO — offers the Applier could not finish

Offers that hit a genuine blocker (captcha / forced registration / missing hard-fact).
Each needs manual handling. See `applier_instructions.md` §7 for the block rules.

Format:
```
- [ ] <company> — <title> — <url>
      reason: <captcha | register | missing-fact: field name>
      note: <one line of context>
```

---

- [ ] Skywise — Intermediate .NET Backend Developer — https://justjoin.it/job-offer/skywise-intermediate-net-backend-developer-gdansk-net
      reason: register
      note: Apply hands off to Airbus Workday ATS (ag.wd3.myworkdayjobs.com); step 1 of 5 is a mandatory "Create Account" (email + password) before any application form. English form → dotnet EN CV.
