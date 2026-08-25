r"""Stage 2: embed every offer title once, cache it, never pay for it again.

Run:  .venv\Scripts\python.exe finder\prototype\semantic\02_embed.py
      ...\python.exe 02_embed.py --force     rebuild even if the cache is current

Writes into finder/data/ (git-ignored):
    emb_title.npy   (N, 384) float32, unit rows — row i is the title of offer ids[i]
    emb_meta.json   model, dim, and ids — ids[i] names the offer in row i

Titles only. The title is free-form prose meaning one thing written fifty ways, which is what
embeddings are for; every other field the finder scores is structured, and stays with the
keyword scorer.
"""

import json
import sys
import time

import numpy as np

import semlib


def build(force=False):
    offers = semlib.load_offers()
    ids = [o["id"] for o in offers]
    print(f"{len(offers)} offers from {semlib.OFFERS_DB.name}")

    if not force and semlib.EMB_META.exists():
        try:
            cache = semlib.load_cache(offers)
            print(f"cache is current ({len(cache)} rows) — nothing to do. --force to rebuild.")
            return cache
        except SystemExit as e:
            print(f"rebuilding: {e}")

    titles = [semlib.title_text(o) for o in offers]
    blank = sum(1 for t in titles if not t)
    if blank:
        print(f"warning: {blank} offers have an empty title and cannot be matched at all")

    t0 = time.perf_counter()
    print("\nembedding titles...")
    title_mat = semlib.encode(titles, progress=True)
    print(f"\nencoded in {time.perf_counter() - t0:.1f}s")

    np.save(semlib.EMB_TITLE, title_mat)
    semlib.EMB_META.write_text(json.dumps({
        "model": semlib.MODEL,
        "dim": int(title_mat.shape[1]),
        "rows": len(ids),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": semlib.OFFERS_DB.name,
        "ids": ids,
    }, ensure_ascii=False), encoding="utf-8")

    norms = np.linalg.norm(title_mat, axis=1)
    print(f"title {title_mat.shape} {title_mat.dtype}  norms {norms.min():.4f}..{norms.max():.4f}")
    for p in (semlib.EMB_TITLE, semlib.EMB_META):
        print(f"  {p.stat().st_size / 1e6:6.1f} MB  {p.name}")
    return semlib.load_cache(offers)


if __name__ == "__main__":
    cache = build(force="--force" in sys.argv)

    # Checkpoint: a warm load must be instant, and row i must still be offer ids[i].
    t0 = time.perf_counter()
    offers = semlib.load_offers()
    cache = semlib.load_cache(offers)
    print(f"\nwarm reload: {time.perf_counter() - t0:.2f}s for {len(cache)} rows")

    i = len(cache) // 2
    v = semlib.encode([semlib.title_text(offers[i])])[0]
    print(f"row {i} re-encodes to cosine {float(cache.title[i] @ v):.4f} with its cached vector "
          f"(1.0000 => row order intact)")
    print(f"  {offers[i]['id']}  {semlib.title_text(offers[i])[:70]}")
