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
- [ ] Anitech Solutions — Manual Tester — https://justjoin.it/job-offer/anitech-solutions-manual-tester-krakow-testing
      reason: dead-link
      note: justjoin Apply hands off to Anitech's PeopleForce ATS, which shows "Zamknięty proces rekrutacyjny" (closed/removed recruitment process) — the posting outlived the employer's own listing.
- [ ] Finture Sp. z o.o. — Programista .Net / Programistka .Net — https://justjoin.it/job-offer/finture-sp-z-o-o--programista-net-programistka-net-warszawa-net-17263598
      reason: missing-fact: Podaj oczekiwania finansowe B2B (zł/h netto)
      note: eRecruiter form requires an hourly B2B net rate (zł/h); profile.md only has a monthly gross figure (10000 PLN) and converting isn't a safe derivation. Everything else on the form was filled and staged for review.
- [ ] Fujitsu Poland Sp. z o.o. — Software Developer with Python, Bash & Linux — https://justjoin.it/job-offer/fujitsu-poland-sp-z-o-o--software-developer-with-python-bash-linux-lodz-python
      reason: register
      note: Apply → Fujitsu's own careers site (jobs.global.fujitsu.com) → "Apply now" hands off to Fujitsu's SAP SuccessFactors portal (career50.sapsf.com); its only entry point is Sign In / "Don't have an account yet?" — no guest-apply path. English form → python EN CV.
- [ ] Data Octopus — Frontend Developer (React / TypeScript) — https://justjoin.it/job-offer/data-octopus-frontend-developer-react-typescript--krakow-javascript
      reason: register
      note: justjoin.it internal Apply modal, this session not logged in (top nav shows "Log in"). Form has no pre-filled profile card; its only consent checkbox literally reads "I'm creating an account, I accept the Terms of Service and Privacy Policy" and is the sole way to accept the required ToS — ticking it creates a new justjoin.it account. No apply_url/external ATS exists for this offer, so there is no alternative path. Stopped before touching any fields.
- [ ] Capgemini Polska — Full Stack Developer (Node.js/React) — https://justjoin.it/job-offer/capgemini-polska-full-stack-developer-node-js-react--krakow-ai
      reason: dead-link
      note: justjoin Apply (top button, ref-click worked) opened a new tab to Capgemini's own careers site (careers.capgemini.com/job/Warszawa-Full-Stack-Developer-.../1393419733/) which reads "Sorry, this position has been filled." — the justjoin listing outlived the employer's own posting.
- [ ] CodeTwo - HRejterzy — Junior Developer ASP.NET — https://justjoin.it/job-offer/codetwo---hrejterzy-junior-developer-asp-net-jelenia-gora-net-399830d1
      reason: dead-link
      note: Apply hand-off lands on codetwo.recruitee.com/o/programista-developer-c-lub-aspnet-2-3 which returns a persistent HTTP 500 (retried once, same result); no form ever appears.
