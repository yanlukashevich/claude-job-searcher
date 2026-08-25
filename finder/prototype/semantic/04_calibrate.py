r"""Stage 4: calibration. What does a cosine of 0.72 actually MEAN on this corpus?

Run:  .venv\Scripts\python.exe finder\prototype\semantic\04_calibrate.py            the battery
      ...\python.exe 04_calibrate.py --q "AI Engineer"    one prototype, full detail
      flags: --bins 40   --ladder (rank ladder for every prototype, not just --q)

Stage 3 said the top of the ranking is trustworthy and gave no way to say where the top ENDS.
A raw cosine cannot say it: the nonsense control still returns 0.54 at rank 1, so 0.54 is
"perfect match" for one query and "no match at all" for another. The fix is to stop reading the
score and read its POSITION — percentiles are per-prototype, so they are comparable when the raw
numbers are not.

Three outputs, in order of what they are for:
  1. distribution + percentile table  — the score->position map for one prototype
  2. rank ladder                      — titles at rank 1, 5, 20, 100, 500, ... The human reads
                                        down it and sees where relevance dies. That row is the
                                        answer to "what percentile is a good match".
  3. cross-prototype matrix           — the same percentile at four different raw scores, which
                                        is the whole argument against a fixed threshold.
  4. noise floor                      — the nonsense control's best score, used as a cut on every
                                        other prototype. It is the only absolute number this
                                        corpus yields, and it lands at a different percentile in
                                        every column.
"""

import sys

import numpy as np

import semlib

# Four wanted directions + one reject + the nonsense control from Stage 3. The control is not
# decoration: its distribution is what "this prototype matched nothing" looks like, and every
# other column is read against it.
PROTOTYPES = [
    ("ai", "AI Engineer / Machine Learning Engineer"),
    ("fullstack", "Fullstack Developer (Python / C# / JavaScript)"),
    ("frontend", "Frontend Developer (React, TypeScript)"),
    ("data", "Data Analyst / Data Analytics Specialist"),
    ("reject:java", "Java Developer (Spring Boot)"),
    ("control", "kitchen assistant, dishwashing, evening shift"),
]

# Reported for every prototype. The tail is dense on purpose — everything we will ever act on
# lives in the last 1%, and p50 is only here to show how far away it is.
PCTS = [50, 75, 90, 95, 99, 99.5, 99.9]

# Ranks to print titles for. Doubling-ish, so the ladder covers 1..1000 in ten rows.
LADDER = [1, 3, 5, 10, 20, 50, 100, 150, 200, 300, 500, 1000]


def histogram(sims, bins=40, width=54):
    counts, edges = np.histogram(sims, bins=bins)
    top = counts.max() or 1
    out = []
    for c, lo, hi in zip(counts, edges[:-1], edges[1:]):
        bar = "#" * int(round(width * c / top))
        out.append(f"  {lo:5.2f}..{hi:5.2f} |{bar:<{width}}| {c:5d}")
    return "\n".join(out)


def pct_table(sims):
    """score -> position, both ways. `above` is the count that survives that cut, because
    'p99' means nothing until you know it is 86 offers out of 8560."""
    n = len(sims)
    rows = [f"  {'pct':>6}  {'cosine':>7}  {'offers above':>12}"]
    for p in PCTS:
        v = float(np.percentile(sims, p))
        rows.append(f"  {p:6.1f}  {v:7.3f}  {int((sims >= v).sum()):12d}")
    rows.append("")
    rows.append(f"  {'cosine':>6}  {'pct':>7}  {'offers above':>12}")
    for t in (0.5, 0.6, 0.7, 0.8):
        above = int((sims >= t).sum())
        rows.append(f"  {t:6.2f}  {100 * (1 - above / n):7.2f}  {above:12d}")
    return "\n".join(rows)


def ladder(offers, sims):
    """The one table a human has to actually read. Where the titles stop being right is the
    percentile the threshold goes at — no metric in this stage can find it for you."""
    n = len(sims)
    order = np.argsort(-sims)
    rows = [f"  {'rank':>5}  {'pct':>6}  {'cos':>5}  title"]
    for r in LADDER:
        if r > n:
            break
        i = order[r - 1]
        rows.append(f"  {r:5d}  {100 * (1 - r / n):6.2f}  {sims[i]:5.3f}  "
                    f"{semlib.title_text(offers[i])[:66]}")
    return "\n".join(rows)


def report(offers, sims, label, query, bins, show_ladder):
    print(f"\n{'=' * 100}\n{label}  {query!r}")
    print(f"  n={len(sims)}  min={sims.min():.3f}  mean={sims.mean():.3f}  "
          f"sd={sims.std():.3f}  max={sims.max():.3f}")
    print(histogram(sims, bins))
    print(pct_table(sims))
    if show_ladder:
        print(ladder(offers, sims))


def matrix(all_sims):
    """Same percentile, one column per prototype. If the raw numbers in a row differed only a
    little, a fixed threshold would be fine and this stage would be pointless."""
    labels = [lab for lab, _ in PROTOTYPES]
    print(f"\n{'=' * 100}\ncosine at each percentile, per prototype")
    print("  " + "pct".rjust(6) + "".join(f"{lab:>14}" for lab in labels))
    for p in PCTS:
        vals = [float(np.percentile(all_sims[lab], p)) for lab in labels]
        print(f"  {p:6.1f}" + "".join(f"{v:14.3f}" for v in vals)
              + f"    spread {max(vals) - min(vals):.3f}")
    print("\n  a raw threshold read off one column is a different percentile in every other one")


def floor(all_sims):
    """The control matched nothing, so its BEST score is what a coincidence is worth on this
    corpus. Anything under it is unreadable — but the count above it differs 8x between
    prototypes, so this is a floor, never a cut-off."""
    ctrl = all_sims["control"]
    cmax = float(ctrl.max())
    n = len(ctrl)
    print(f"\n{'=' * 100}\nnoise floor = the control's best hit = {cmax:.3f}")
    for lab, _ in PROTOTYPES:
        if lab == "control":
            continue
        above = int((all_sims[lab] >= cmax).sum())
        print(f"  {lab:>12}  {above:5d} offers above it  = p{100 * (1 - above / n):.2f}")
    print("  same raw floor, percentiles 10 points apart: how many real matches a corpus holds\n"
          "  is a property of the corpus, and no single percentile can stand in for it")


if __name__ == "__main__":
    args = sys.argv[1:]

    def opt(flag, default):
        return args[args.index(flag) + 1] if flag in args else default

    bins = int(opt("--bins", 40))

    offers = semlib.load_offers()
    cache = semlib.load_cache(offers)
    print(f"{len(cache)} offers, model {cache.meta['model'].split('/')[-1]}, "
          f"built {cache.meta['built_at']}")

    if "--q" in args:
        q = opt("--q", "")
        report(offers, cache.sims(semlib.encode_query(q)), "query", q, bins, True)
    else:
        all_sims = {}
        for label, q in PROTOTYPES:
            all_sims[label] = cache.sims(semlib.encode_query(q))
            report(offers, all_sims[label], label, q, bins, "--ladder" in args)
        matrix(all_sims)
        floor(all_sims)
