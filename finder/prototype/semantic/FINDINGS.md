# Findings — `paraphrase-multilingual-MiniLM-L12-v2`

Measured with `01_playground.py`, `03_explore.py` and `04_calibrate.py`. Every number is reproducible by rerunning
them. All of it is model-specific: **change the model and this file is void.**

Scope: semantic matching runs on **offer titles only**. Everything else the finder scores stays
with the keyword scorer.

Stage 0 facts: 384 dims, `max_seq_length` **128 tokens**, CPU, ~7.5 s to load.
The longest title in the corpus costs ~23 tokens, so nothing is ever truncated.

## The four things that change what we build

### 1. The cross-language bridge is *title*-shaped, not language-shaped

| pair | cos |
|---|---|
| `Inżynier oprogramowania` / `Software Engineer` | **0.970** |
| `Programista Java` / `Java Developer` | **0.923** |
| `Programista Python` / `Python Developer` | **0.928** |
| `Analityk danych` / `Data Analyst` | **0.870** |
| `Praca zdalna` / `Remote work` | **0.408** |
| `Zdalnie` / `Remotely` | **0.460** |

Job titles bridge PL↔EN essentially perfectly — the entire premise, and it holds on real data:
the query `AI Engineer / Machine Learning Engineer` returns
`Osoba do pracy w obszarze sztucznej inteligencji (AI)` at 0.866 and
`Inżynier uczenia maszynowego - Agentic AI` at 0.815, neither of which shares a word with it.

Generic employment phrases do **not** bridge. The giveaway: `Praca zdalna` / `Praca stacjonarna`
— *opposites* — scores **0.799**, because both begin with "Praca". Outside job-title vocabulary
the model groups by surface form and language.

→ Prototypes are written as job titles, never as sentences about what Yan wants.
→ Independent confirmation of Stage 7: workplace and remote must never route through embeddings;
here the model scores an opposite at 0.80.

### 2. Cosine tracks shared literal words more than it tracks meaning

| pair | cos | |
|---|---|---|
| `Data Analyst` / `Data Engineer` | **0.826** | different jobs |
| `Data Analyst` / `Data Scientist` | **0.824** | different jobs |
| `AI Engineer` / `Machine Learning Engineer` | **0.599** | synonyms in this market |
| `AI Engineer` / `ML Engineer` | **0.609** | synonyms |
| `Artificial Intelligence Engineer` / `Machine Learning Engineer` | **0.708** | synonyms, spelled out |

The shared token "Data" beats the actual synonymy of AI and ML. Spelling out "Artificial
Intelligence" recovers 0.11 — the model knows the long form better than the acronym.

→ Each direction needs **several phrasings**, using the words postings actually use (`AI`,
`Machine Learning`, `LLM`, `Sztuczna inteligencja`); the model will not infer them from one
canonical label. A second, independent argument for `max()` over a set rather than one vector.

### 3. Length moves the score on its own

`Python Developer` / `Java Developer` = **0.388**.
`Python Developer` / `Java Developer (Spring Boot)` = **0.231**.

Two extra words, no change of meaning, −0.157.

→ Keep prototypes title-length. → **Never compare raw cosines from prototypes of different
lengths** — which is why Stage 4 expresses thresholds as percentiles, and why a `max()` over
prototypes of uneven length lets the longest one silently lose every time.

### 4. Stacks separate cleanly — the floor is ~0.09

| pair | cos |
|---|---|
| `Python Developer` / `C# Developer` | 0.483 |
| `Java Developer` / `C# Developer` | 0.576 |
| `Python Developer` / `Java Developer` | 0.388 |
| `Python Developer` / `JavaScript Developer` | 0.366 |
| `Embedded C Developer` / `Sales Manager` | 0.107 |
| `Python Developer` / `Truck driver` | 0.089 |

Better than feared: "Developer" does not hold wrong-stack pairs up near the right ones.

The one apparent counter-example was token noise, not language: `Python Developer` /
`Kierowca kat. C+E` = 0.334, but `Python Developer` / `Kierowca ciężarówki` = **0.094**. The
0.334 is the literal `C` in the licence class colliding with C the language. Stray token
collisions are the noise floor to expect when hunting surprises.

## The documented failure modes: confirmed, with a correction

Negation. The plan's example understates it; the controlled version restores it:

| pair | cos | |
|---|---|---|
| `Java` / `no Java, we use Python` | 0.401 | looks like the model "got it" — it didn't; 15 extra tokens diluted a 1-token query (finding 3) |
| `we use Java` / `we do not use Java` | **0.773** | same length, one word apart. The NOT is nearly free. |
| `remote work` / `no remote work, on-site only` | **0.747** | |
| `remote work` / `on-site only` | 0.255 | the negated phrase *staying in the text* is what scores |

Numbers. Confirmed, no nuance: `8000 PLN` / `25000 PLN` = **0.608**; `2 years of experience` /
`10 years of experience` = **0.817**.

→ Kill-words and salary stay in Python. Note the same trap already applies to the *existing*
keyword scorer: a posting saying "no Java here" trips a naive `java` kill too.

## Register: write prototypes as titles

| prototype | vs `Python Developer` |
|---|---|
| `Senior Python Developer (Remote)` | **0.809** |
| `I want a remote Python job` | 0.619 |
| `Python, Django, PostgreSQL, Docker` | 0.570 |

A first-person wish loses 0.19 against an equivalent title; a bare tag list loses 0.24. The same
effect on the corpus: `AI Engineer` scores 1.000 against its own matches, the tag list
`AI, LLM, RAG, PyTorch` only 0.752.

## Working scale for titles

```
0.90+  same job, other language / trivially reworded
0.75+  same family, real overlap  ... or two titles sharing a prominent literal word
0.55   related but distinct roles
0.35   same industry, wrong stack
0.10   unrelated
```

The plan's predicted 0.25–0.75 squash does **not** hold for short title-vs-title pairs; the
usable range is much wider. Over the whole corpus it is wrong in the other direction — the mass
sits lower, at 0.15–0.40. See the Stage 4 section.

## Corpus notes

- 8560 offers as of the 2026-08-21 harvest, all with an id and a title. The db is **rewritten
  whole** on every harvest, so `row i == line i` survives only until the next one — hence the id
  check on load. It has already fired once in anger.
- **695 offers (8.8%) have a title naming no stack at all** — `Software Engineer`, `Programista`,
  `Specjalista/ka ds. Automatyzacji Procesów`. Semantic title matching cannot rank these; the
  keyword scorer is what reaches them.
- Tutoring roles (`Coding Tutor`, `Korepetytor online - Python`, all KODLAND) are 20 offers,
  0.25% of the corpus, and sit at rank 255+ for every direction — 0 in any top 20. They get no
  negative prototype; `check:teaching` in `03_explore.py` exists to notice if that changes.
- **Every offer has a `category`, and it is not a usable label.** 43 values over two disjoint
  vocabularies: justjoin's is *language*-shaped (`python`, `java`, `javascript`, `net`, `ai`,
  `data`) and pracuj's is *role*-shaped (`backend`, `frontend`, `fullstack`, `ai-ml`,
  `big-data-science`, `it-other`). Neither portal uses the other's words — justjoin has no
  `frontend`, pracuj has no `python`. Worse, a pracuj offer can sit in several specializations
  and `harvest_pracuj.py` keeps whichever pass ran first, so `SPECS` order decides the label:
  `backend` is first and `ai-ml` last, which is why `AI Engineer` appears under `architecture`
  and `Data Analyst` under `backend`. Of the semantic top 100 for the `ai` prototype, 28 carry
  neither `ai` nor `ai-ml`; of the 271 offers that do carry one, the median semantic rank is 223.
  → Useful as a coarse facet in the cockpit, useless as ground truth for Stage 6 and as a label
  for Stage 8.

## Stage 4: what a cosine is worth on this corpus

Measured with `04_calibrate.py` over all 8560 titles, six prototypes (four wanted directions,
one reject, one nonsense control).

### The corpus-wide distribution is lower and wider than the plan predicted

| prototype | mean | sd | max | p99 | p99.9 |
|---|---|---|---|---|---|
| `Data Analyst / Data Analytics Specialist` | 0.385 | 0.133 | 0.929 | 0.784 | 0.905 |
| `AI Engineer / Machine Learning Engineer` | 0.334 | 0.124 | 0.871 | 0.760 | 0.804 |
| `Frontend Developer (React, TypeScript)` | 0.259 | 0.120 | 0.994 | 0.640 | 0.847 |
| `Fullstack Developer (Python / C# / JavaScript)` | 0.245 | 0.140 | 0.844 | 0.687 | 0.783 |
| `Java Developer (Spring Boot)` | 0.162 | 0.125 | 0.880 | 0.585 | 0.638 |
| control: `kitchen assistant, dishwashing…` | 0.186 | 0.090 | **0.543** | 0.415 | 0.487 |

The plan expected mass around 0.45 in a 0.25–0.75 band. The real mass sits around **0.15–0.40**
and the distribution is a smooth right-skewed hump with no gap in it — there is no visible
"matches" mode to threshold at. Everything ever acted on lives in the **last 1%**: p99 is 86
offers, p99.9 is ~10.

### Raw thresholds are not portable — as predicted, and worse than predicted

At p99 the six prototypes sit at 0.415–0.784: **spread 0.37**, which is larger than the gap
between "same job family" and "unrelated" on the Stage 1 scale. `cos >= 0.70` keeps 157 offers
for `ai`, 69 for `fullstack`, 5 for `java` and 0 for the control.

### …but percentiles are not portable across prototypes either

The one absolute number this corpus yields is the **noise floor: 0.543**, the control's best hit.
It matched nothing, so that score is what a coincidence is worth here. Applied as a cut:

| prototype | offers above 0.543 | = percentile |
|---|---|---|
| data | 973 | p88.6 |
| ai | 481 | p94.4 |
| fullstack | 381 | p95.6 |
| frontend | 235 | p97.3 |
| java | 125 | p98.5 |

Same raw floor, percentiles **ten points apart**, because how many data-ish or frontend-ish jobs
the market actually posts is a property of the corpus, not of the threshold. So:

→ **A percentile is portable across harvests** (the corpus grows; p99 stays "the top 1%") **and
not across prototypes.** Use it to keep one prototype's cut stable over time. Never to compare
two prototypes — that is what Stage 5's subtraction is for.

### Where relevance actually dies (the checkpoint answer)

Reading the rank ladders down until the titles stop being right:

| prototype | last good rank | its cosine | percentile |
|---|---|---|---|
| ai | ~250 (`AI Developer (Java&Python)`); rank 300 is already `Wykonawca usług programowania`, 500 is `QA Engineer` | 0.64 | p97.1 |
| frontend | ~200 (`Software Engineer 2 (Java/Kotlin) – Frontend Platform`); 250 is `Backend (Python) Junior` | 0.56 | p97.7 |
| fullstack | ~500 (`Senior Fullstack Developer (React + Kotlin)` — right role, wrong stack, which is a *hard filter's* job); 1000 is `ServiceNow Developer` | 0.50 | p94.2 |
| data | ~500 (`Data Engineer (DevOps)`); 1000 is `Informatyk / TSG Specialist` | 0.63 | p94.2 |

**A good match sits above p99** (top ~86, cosine 0.59–0.78 depending on prototype). The band
p97–p99 is worth reading. Below the 0.543 noise floor nothing is worth reading, and the floor is
reached between p88 and p98.5 depending on prototype. Both cuts are needed: the percentile bounds
the *list length*, the floor bounds the *quality*.

### `max()` over positives is biased toward the hottest prototype — and it does not matter

`data` outscores `frontend` by ~0.13 of mean on every offer, so a raw `argmax` over the four
positives hands **4633 of 8560 offers to `data`** and only 745 to `frontend`. Ranking each
prototype's scores to percentiles first and taking the argmax of *that* moves 2272 offers (27%)
to a different label.

All 2272 sit in the noise band. Inside the top 600 by score, raw and rank disagree on **5 offers**,
and every one is a genuine near-tie: `Fullstack Developer (TypeScript, React, Node.js)` at
frontend 0.77 / fullstack 0.75, `Data Scientist / Machine Learning Engineer` at data 0.73 / ai 0.71.

→ Stage 5 can take `max()` on raw cosines. Normalising per prototype buys nothing where decisions
are made and adds a corpus-dependent step. Revisit only if a positive is added whose baseline is
far outside 0.25–0.39.

### Corpus note: 20% of titles are duplicates

6875 distinct titles over 8560 offers; 2275 offers share a title with another (`DevOps Engineer`
×53, `Data Engineer` ×42, `Java Developer` ×41). Identical titles produce identical vectors, so a
top-20 can be one title repeated — visible as the `java` ladder sitting flat at 0.638 from rank 10
to rank 20, and as `Data Analyst` filling ranks 3–20. Ranking is unaffected; a human reading a
top-k list is. Dedupe by title when Stage 9 renders one.

## Checkpoints

**Stage 1** — passed. `01_playground.py --quiz` is the self-test: guessing within ~0.08 mean
error means the scale above is internalised. The three predictions this exercise got *wrong* —
the remote-work bridge, `Data Analyst`/`Data Engineer` outranking `AI`/`ML`, and length
outweighing stack — are findings 1, 2 and 3, and each one constrains Stage 5.

**Stage 2** — passed. `(N, 384)` float32, all norms exactly 1.0, ~176 s to build, ~0.2 s to
reload, and one row re-encoded to cosine 1.0000 against its cached vector.

**Stage 4** — passed, with one correction to the plan. Thresholds go in as percentiles *per
prototype over time*, not as one percentile shared by all prototypes; and they need the 0.543
noise floor beside them, because a percentile alone will happily return 900 data-flavoured
non-matches. `04_calibrate.py --ladder` regenerates every number above; rerun it after any
harvest large enough to move the corpus.

**Stage 3** — passed. The title ranking is trustworthy at the top: across the probe battery, zero
reject-titled offers reached any top 20, and each wanted direction returned its own roles in both
languages at 0.81–0.98. It is *not* trustworthy for the 8.8% with stackless titles, and a
nonsense control (`kitchen assistant, dishwashing, evening shift`) still returns 0.54 at rank 1 —
**there is no absolute "no match" score.** That is exactly why Stage 4 calibrates percentiles and
Stage 5 subtracts a negative instead of thresholding a raw cosine.
