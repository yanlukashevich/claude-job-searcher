# Semantic scoring — build plan

Embedding-based offer matching for the finder. Goal: replace/augment the keyword score with a
**content-based recommender** — offers ranked by vector similarity to prototypes of what Yan
wants and doesn't want.

Not RAG. There is no generation step; the retrieved thing *is* the output. (RAG would be a
separate, later idea: retrieving past `composed_answers` from `applications_log.jsonl` as
few-shot examples for the applier subagent.)

## Design constraints

- **Lives in `finder/prototype/semantic/`** — inside the finder, outside `src/`, so nothing
  here ever enters a subagent's Cowork mount.
- **Local model, no API.** Corpus is ~8.6k short titles and grows with every harvest; re-indexing must be free so tuning
  isn't rate-limited by cost.
- **Multilingual is mandatory**, not a preference: `"Programista Python"` and
  `"Python Developer"` must land close, which only happens in a shared cross-lingual space.
- **Embed the title, nothing else.** The title is the one free-form field: it means one thing
  written fifty ways, in two languages, which is what a model is for. Never one vector for the
  whole offer — full descriptions are ~90% shared boilerplate and averaging destroys the
  distinction that matters.
- **Hard constraints never go through embeddings.** Salary, seniority, remote/hybrid, kill-words
  are arithmetic and booleans. Embeddings cannot do negation, numbers, or comparisons.

Target architecture:

```
1. HARD FILTERS (plain Python)   salary, workplace, level, kill-words
     |  deterministic, debuggable, free
2. SEMANTIC MARGIN               max(sim to positives) - max(sim to negatives)
     |  over offer TITLES; ranks what survived
3. HUMAN                         the cockpit
```

## Scope: titles only

Semantic matching runs on the **offer title** and on nothing else. Every other field the finder
scores — skills, kill-words, salary, seniority, workplace — is structured data, and stays with
the keyword scorer where it already works.

That leaves two scores, and they must stay two: a continuous margin next to an unbounded integer
point-sum will let one silently dominate the other if added. Two sortable columns in the cockpit
(Stage 9); the human combines them. The rows where they disagree are the most informative ones
there are, and fusing hides them.

---

## Stage 0 — Environment

`sentence-transformers` pulls `torch`, `transformers`, `tokenizers`, `scipy`,
`huggingface-hub`. On Windows the default PyPI torch wheel is CPU-only (~200 MB, not the
multi-GB CUDA one). Expect ~1 GB installed + ~470 MB model cache in `~/.cache/huggingface`.

Isolated in a venv so the finder keeps running on global Python untouched.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install sentence-transformers numpy
```

**Model:** `paraphrase-multilingual-MiniLM-L12-v2` — 384 dims, ~470 MB, 50+ languages
including Polish, no prefix requirements. Swap later only if Stage 6 justifies it.

**Checkpoint:** model loads; `embedder.max_seq_length` prints a number. Write that number down —
it is the silent-truncation limit.

## Stage 1 — Similarity playground

One script, ~15 lines: text pairs in, cosine out. No data files.

Things to actually test:

- Cross-language bridge: `"Programista Python"` vs `"Python Developer"`
- Near-misses: `"Python Developer"` vs `"Python Data Engineer"` vs `"PHP Developer"`
- Far apart: `"Embedded C Developer"` vs `"Sales Manager"`
- **The documented failure modes** — verify, don't trust:
  - `"Java"` vs `"no Java, we use Python"` → comes out CLOSE (no logical NOT)
  - `"8000 PLN"` vs `"25000 PLN"` → nearly identical (no number sense)
- Register asymmetry: `"I want a remote Python job"` vs a real title, then a fake job-ad
  phrasing vs the same title.

**Checkpoint:** you can predict roughly where a pair lands before running it.

## Stage 2 — Embed the corpus

Read `finder/data/offers_db.jsonl` → cache:

```
finder/data/emb_title.npy    (N, 384) float32
finder/data/emb_meta.json    { model, dim, ids: [...] }   # row order MUST match
```

- `normalize_embeddings=True` so dot product == cosine
- `batch_size=64`, progress bar; expect 2–5 min on CPU
- store the model name in meta — future-you must know which model produced these
- store the ids in meta and **check them on every load**. The db is rewritten whole on each
  harvest, so `row i == line i` holds only until the next one; a stale matrix still loads
  cleanly and returns plausible nonsense

**Checkpoint:** shapes match; re-run loads from cache in <1s.

## Stage 3 — Nearest-neighbour explorer

Type a text → 20 most similar offers with scores.

```
> AI Engineer / Machine Learning Engineer
0.871  AI Engineerka / AI Engineer                            VeloBank
0.866  Osoba do pracy w obszarze sztucznej inteligencji (AI)  AGH
0.815  Inżynier uczenia maszynowego - Agentic AI (K/M/X)      COMARCH
```

Rows 2 and 3 share no word with the query. That is the whole reason this exists.

Throw all four wanted directions at it (AI; fullstack Python/C#/JavaScript; data analysis;
frontend), then the rejects (testing, helpdesk, gamedev, Java), then weird stuff — a Polish
query, a full sentence, and something with no match at all as a control.

Hunt the surprises — a high-ranked wrong offer teaches more than fifty correct ones. Those
become negative prototypes in Stage 5.

**Checkpoint:** a written opinion, backed by named offers, on where the ranking is trustworthy
and where it is not.

## Stage 4 — Calibration

Score all offers against one prototype; histogram + percentiles.

Expect everything squashed into a narrow band. This means a raw cosine threshold is not portable
— **express every threshold as a percentile**, not a raw score.

**Checkpoint:** you know what percentile a "good match" sits at.

*Done — `04_calibrate.py`, results in `finder/prototype/semantic/FINDINGS.md`. Measured mass is
0.15–0.40, not 0.25–0.75; a good match sits above **p99**. One correction: a percentile is
portable across harvests but **not across prototypes** (the same raw score is p88.6 for `data`
and p98.5 for `java`), so every cut carries a percentile for list length plus the measured
**0.543 noise floor** for quality.*

## Stage 5 — Prototypes: positives and negatives

```python
score = max(sim to any positive) - max(sim to any negative)
out   = (score, which_positive_won, which_negative_was_closest)
```

Four positives — **ai, fullstack (Python/C#/JavaScript), data, frontend** — and four negatives:
java, qa, helpdesk, gamedev. **Always carry the two labels out** — `0.31 — matched:frontend,
reject:gamedev` is debuggable; a bare number is not.

No teaching negative: tutoring titles sit at rank 255+ for every direction (0 in any top 20)
and number 20 in the whole corpus. A negative prototype that never fires is a text to maintain
for nothing.

Each positive needs several phrasings, in both languages, because the model scores shared
literal words above synonymy (`AI Engineer` vs `ML Engineer` = 0.61).

Why `max()` and not an averaged "taste vector": averaging four distant directions yields their
centroid, which encodes only "generic IT job" — and Java/QA/helpdesk sit *closer* to generic-IT
than a real match does. The average actively ranks the kills above the matches.

Why negatives don't contradict "embeddings can't do negation": the NOT lives in Python (a
subtraction), not in the text. We measure distance to a reject region and subtract it ourselves.

Then iterate on prototype *text* — instant, no re-indexing. Write prototypes title-shaped: a
first-person wish loses ~0.19 to an equivalent title, and cross-register costs 0.25–0.40.

**Checkpoint:** known-good vs known-bad offers produce a clear margin gap with sensible labels.

## Stage 6 — Evaluate against real decisions

Ground truth already in the repo:

- `src/applications_log.jsonl` — ~301 applications
- `finder/data/manual_applied.json` — manual marks
- `finder/data/manual_scores.json` — explicit rejects **with reasons** (`"java"`, `"senior"`);
  small, but the highest-quality label available because the *why* is recorded

Measure:

- Where do applied-to offers land in the semantic ranking? Top 10% = it works.
- Where do explicit rejects land? Any reject in the top 10% is a bug worth reading.
- **Head-to-head vs the existing keyword score.** Rank both ways, read the offers where they
  disagree most. That disagreement set is the whole lesson.

Headline metric: `recall@k` — of the offers applied to, how many were in the semantic top 100?

**Checkpoint:** a number worth quoting, and a decision whether to continue.

## Stage 7 — Hard filters in front

Only after Stage 6 works. Wrap the semantic score in the funnel above. Salary/seniority/
workplace must not route through embeddings.

## Stage 8 — Learn it from behaviour

Once a few hundred decisions have accumulated, replace hand-written prototypes with logistic
regression over the same embeddings (labels: applied=1, skipped=0). Learns preferences that
were never articulated, and updates itself on every tick. Same embedding cache — Stages 2–6
are not wasted.

## Stage 9 — Into the cockpit

A `sem` column beside the existing score: sortable, showing margin + matched prototype label.
Run both scores in parallel before retiring the keyword one. **Keep the keyword kills
regardless** — they encode hard rules embeddings cannot express.

---

## Known limits (do not design around these — design *for* them)

| Embeddings cannot | Consequence |
|---|---|
| Negation (`"no Java"` ≈ `"Java"`) | Kill rules stay in Python |
| Numbers / comparison (`8000` ≈ `25000`) | Salary filter stays arithmetic |
| Hard booleans (remote, seniority) | Stay booleans; don't launder them into a score |
| Absolute thresholds | Calibrate per model+corpus; use percentiles |
| Multi-hop ("pays more than the Kraków one") | Needs an agent loop, not one lookup |

Changing the embedding model invalidates every cached vector. Re-index on any model change.
