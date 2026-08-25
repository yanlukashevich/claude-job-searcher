r"""Stage 3: nearest-neighbour explorer. Type a text, get the offer titles nearest to it.

Run:  .venv\Scripts\python.exe finder\prototype\semantic\03_explore.py            REPL
      ...\python.exe 03_explore.py --probe                 the canned battery
      ...\python.exe 03_explore.py --q "AI Engineer"       one shot
      flags: -k 20

The point is not to admire the correct hits. It is to find the WRONG offer sitting at rank 3 —
that one names a negative prototype for Stage 5, and fifty correct hits name nothing.

Queries are written title-shaped on purpose: a wish ("I want a remote Python job") or a bare
tag list loses 0.19-0.40 against an equivalent title. Match the register of what you search.
"""

import sys

import numpy as np

import semlib

# The four directions Yan applies to, the rejects, then deliberately awkward inputs.
PROBES = [
    ("want:ai", "AI Engineer / Machine Learning Engineer"),
    ("want:fullstack", "Fullstack Developer (Python / C# / JavaScript)"),
    ("want:frontend", "Frontend Developer (React, TypeScript)"),
    ("want:data", "Data Analyst / Data Analytics Specialist"),
    ("reject:qa", "Manual QA Tester"),
    ("reject:helpdesk", "IT Support Specialist / Helpdesk"),
    ("reject:gamedev", "Unity Game Developer"),
    ("reject:java", "Java Developer (Spring Boot)"),
    # Not a reject prototype — a watch query. Tutoring roles sit at rank 255+ for every
    # direction, so they need no negative of their own. Kept to notice if that changes.
    ("check:teaching", "Nauczyciel programowania / Coding Tutor"),
    ("weird:polish", "Programista Python"),
    ("weird:sentence", "I want a remote junior job where I can learn AI"),
    ("weird:nonsense", "kitchen assistant, dishwashing, evening shift"),
]


def fmt(offers, idx, score):
    o = offers[idx]
    # company and tags are printed as context for the human reading the list; nothing but the
    # title is scored.
    return (f"  {score:5.3f}  {semlib.title_text(o)[:54]:<54}  {(o.get('company') or '')[:24]:<24}"
            f"  {', '.join(o.get('skills') or [])[:40]}")


def top(cache, query, k):
    sims = cache.sims(semlib.encode_query(query))
    idx = np.argpartition(-sims, min(k, len(sims) - 1))[:k]
    return sorted(idx, key=lambda i: -sims[i]), sims


def show(cache, offers, query, k):
    order, sims = top(cache, query, k)
    print(f"\n{'=' * 100}\n{query!r}   (top {k} spread {sims[order[0]]:.3f}..{sims[order[-1]]:.3f})")
    for rank, i in enumerate(order, 1):
        print(f"{rank:3d}." + fmt(offers, i, sims[i]))
    return order


def repl(cache, offers, k):
    print(f"k={k}. Enter a query (blank or Ctrl-C to quit).\n")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not q:
            return
        show(cache, offers, q, k)


if __name__ == "__main__":
    args = sys.argv[1:]

    def opt(flag, default):
        return args[args.index(flag) + 1] if flag in args else default

    k = int(opt("-k", 20))

    offers = semlib.load_offers()
    cache = semlib.load_cache(offers)
    print(f"{len(cache)} offers, model {cache.meta['model'].split('/')[-1]}, "
          f"built {cache.meta['built_at']}")

    if "--probe" in args:
        for label, q in PROBES:
            print(f"\n\n########## {label}")
            show(cache, offers, q, k)
    elif "--q" in args:
        show(cache, offers, opt("--q", ""), k)
    else:
        repl(cache, offers, k)
