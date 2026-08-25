r"""Stage 4 companion: one prototype, one long human-readable report.

Run:  .venv\Scripts\python.exe finder\prototype\semantic\05_report.py > report.txt
      ...\python.exe 05_report.py --q "Frontend Developer (React)" --cat frontend,javascript
      flags: --n 100 (slice size)   --cat ai,ai-ml (which categories to list in full)

04_calibrate.py answers "where is the cut". This answers "what is actually IN the list" — the
same distribution, but with 300 titles printed out of it: the top, the middle and the bottom.
Reading the middle is the point. The top is obvious and the bottom is obvious; the band around
the median is where you find out what the score is really doing.

Each line carries the offer's portal `category`, which is NOT ground truth (two disjoint
vocabularies, and pracuj's is decided by harvest pass order — see FINDINGS.md). It is printed
so the two labellings can be read against each other, not so one can check the other.
"""

import sys

import numpy as np

import semlib

DEFAULT_Q = "AI Engineer / Machine Learning Engineer"
PCTS = [50, 75, 90, 95, 99, 99.5, 99.9]


def histogram(sims, bins=40, width=54):
    counts, edges = np.histogram(sims, bins=bins)
    top = counts.max() or 1
    for c, lo, hi in zip(counts, edges[:-1], edges[1:]):
        print(f"  {lo:5.2f}..{hi:5.2f} |{'#' * int(round(width * c / top)):<{width}}| {c:5d}")


def line(offers, sims, order_pos, i, n):
    o = offers[i]
    return (f"  {order_pos:5d}  {100 * (1 - order_pos / n):6.2f}  {sims[i]:5.3f}  "
            f"[{(o.get('category') or '?'):<21}] {semlib.title_text(o)[:56]:<56}  "
            f"{(o.get('company') or '')[:22]}")


def slice_out(offers, sims, order, start, count, heading):
    n = len(sims)
    print(f"\n{'=' * 120}\n{heading}  (ranks {start + 1}-{min(start + count, n)})")
    print(f"  {'rank':>5}  {'pct':>6}  {'cos':>5}  {'category':<23} {'title':<56}  company")
    for r in range(start, min(start + count, n)):
        print(line(offers, sims, r + 1, order[r], n))


def by_category(offers, sims, order, wanted):
    """Every offer carrying one of these categories, best score first, with its global rank."""
    n = len(sims)
    rank = np.empty(n, dtype=int)
    rank[order] = np.arange(1, n + 1)
    rows = [i for i in range(n) if (offers[i].get("category") or "") in wanted]
    rows.sort(key=lambda i: -sims[i])
    print(f"\n{'=' * 120}\nEVERY offer in category {'/'.join(sorted(wanted))} — {len(rows)} offers, "
          f"scored against this prototype")
    if not rows:
        return
    s = np.array([sims[i] for i in rows])
    r = np.array([rank[i] for i in rows])
    print(f"  mean {s.mean():.3f}  median {np.median(s):.3f}  min {s.min():.3f}  max {s.max():.3f}")
    print(f"  global rank: best {r.min()}, median {int(np.median(r))}, worst {r.max()}   |   "
          f"in top 100: {(r <= 100).sum()}   top 300: {(r <= 300).sum()}   "
          f"below the 0.543 noise floor: {(s < 0.543).sum()}")
    print(f"\n  {'rank':>5}  {'pct':>6}  {'cos':>5}  {'category':<23} {'title':<56}  company")
    for i in rows:
        print(line(offers, sims, int(rank[i]), i, n))


if __name__ == "__main__":
    args = sys.argv[1:]

    def opt(flag, default):
        return args[args.index(flag) + 1] if flag in args else default

    q = opt("--q", DEFAULT_Q)
    count = int(opt("--n", 100))
    wanted = set(opt("--cat", "ai,ai-ml").split(","))

    offers = semlib.load_offers()
    cache = semlib.load_cache(offers)
    sims = cache.sims(semlib.encode_query(q))
    order = np.argsort(-sims)
    n = len(sims)

    print(f"{'=' * 120}\nPROTOTYPE: {q!r}\n{n} offers, model "
          f"{cache.meta['model'].split('/')[-1]}, cache built {cache.meta['built_at']}")
    print(f"\n  min={sims.min():.3f}  mean={sims.mean():.3f}  sd={sims.std():.3f}  "
          f"max={sims.max():.3f}\n")
    histogram(sims)
    print(f"\n  {'pct':>6}  {'cosine':>7}  {'offers above':>12}")
    for p in PCTS:
        v = float(np.percentile(sims, p))
        print(f"  {p:6.1f}  {v:7.3f}  {int((sims >= v).sum()):12d}")

    slice_out(offers, sims, order, 0, count, "TOP — the best matches")
    slice_out(offers, sims, order, (n - count) // 2, count, "MIDDLE — around the median")
    slice_out(offers, sims, order, n - count, count, "BOTTOM — the worst matches")
    by_category(offers, sims, order, wanted)
