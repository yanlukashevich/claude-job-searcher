# Offer triage — keyword scorer + review page

A code-only keyword filter/scorer over the harvested justjoin.it offers
(`../data/offers_db.jsonl`). This is the Finder's triage step: `harvest.py` fills the offer
DB, this scores it into a clickable review page. See `../README.md` for the whole pipeline.

## The idea

Code decides **facts** (is a keyword present?), never judgment. The number only **orders**
offers; later an LLM makes the actual keep/reject call. Every offer lands in one bucket:

| bucket | meaning |
|---|---|
| `1_KILL`   | a forbidden word appeared (SAP, Salesforce, a design/security *role* in the title…) |
| `2_VETO`   | the title names someone else's stack (Java, PHP, mobile…) and no core tech |
| `3_NEG`    | score ≤ 0 |
| `4_WEAK`   | score 1–4 |
| `5_PLAUS`  | score 5–9 |
| `6_STRONG` | score ≥ 10 |

Score = `2×(title keywords) + role/seniority + skills keywords`. A title keyword counts
double because the title names the job. Role words (backend, fullstack, analyst, manager…)
are scored by the ROLE table, not as keywords, so they are never counted twice.

The scale (in `keywords.py`) is about **identity, not difficulty**:
`+3` this is my job · `+1` no signal, or one step away · `−1` a different *kind* of dev ·
`−3` a different profession · `KILL` never.

## Files

- **`keywords.py`** — the classification. **This is the file you edit.** Move a word between
  the five lists, save, regenerate.
- `scoring.py` — the engine (regex traps, the veto, the ROLE table, `classify()`). Rarely edited.
- **`browse.py`** — reads the offers, scores them, writes `offers.html`.
- `offers.html` — the review page (generated; git-ignored is fine).

## Use

```bash
python keywords.py     # sanity check: bucket sizes, no word in two lists
python browse.py       # regenerate offers.html
python browse.py --open # regenerate and open in the browser
```

Then open `offers.html`. It shows a **category × bucket grid**; click any cell to see exactly
the offers that landed there, sorted by score, each linking to the posting. Click a row or
column label for a whole row / column. The search box filters the visible list by
title / company / skill. Tuning loop: edit `keywords.py` → `python browse.py` → refresh tab.

## Known open items

- `harvest.py` discards the list API's `languages`, `niceToHaveSkills`, and
  `requiredSkills[].level`. Missing `languages` is why some German/French postings survive.
- Vendor spelling variants leak (`sap ecc`/`sap hana` not killed; `react.js` ≠ `reactjs`).
- A skills-side veto (Java in the *skills* with no core tech) is not yet implemented — a few
  Java jobs with neutral titles still reach `6_STRONG`.
- The justjoin **category** is a stronger signal than any keyword and is currently unused by
  the score. Candidate policy: hard-keep js/python/net/html; drop java/php/mobile/ux/erp/pm/
  analytics/game/security unless very high; let the score decide the rest.
