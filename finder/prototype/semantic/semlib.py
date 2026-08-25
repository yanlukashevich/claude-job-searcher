r"""Shared bits for the semantic stages. Stage scripts are numbered, so they cannot import
each other (`import 02_embed` is a syntax error) — anything two stages need lives here.

Titles only. Semantic matching runs on the offer title and nothing else; skills, kill-words,
salary, seniority and workplace all stay with the finder's keyword scorer.

Follows finder/common.py's Windows rules: always encoding='utf-8', never let a print crash.
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "data"          # finder/data
OFFERS_DB = DATA / "offers_db.jsonl"

EMB_TITLE = DATA / "emb_title.npy"
EMB_META = DATA / "emb_meta.json"

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_offers():
    """Every offer ever seen, in file order. That order defines the embedding row order."""
    with open(OFFERS_DB, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def title_text(row):
    return (row.get("title") or "").strip()


_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL)
    return _model


def encode(texts, batch_size=64, progress=False):
    """Unit-length rows, so a dot product IS the cosine."""
    return get_model().encode(
        list(texts), batch_size=batch_size, normalize_embeddings=True,
        show_progress_bar=progress, convert_to_numpy=True).astype(np.float32)


def encode_query(text):
    return encode([text])[0]


class Cache:
    """The Stage 2 artifact, loaded and checked against the offers file it claims to describe."""

    def __init__(self, ids, title, meta):
        self.ids, self.title, self.meta = ids, title, meta
        self.index = {oid: i for i, oid in enumerate(ids)}

    def __len__(self):
        return len(self.ids)

    def sims(self, query_vec):
        """Cosine of one query against every offer title, as one matrix multiply."""
        return self.title @ query_vec


def load_cache(offers=None):
    """Raises if the cache is missing, stale, or from a different model — a silently mismatched
    row order is the one bug in this pipeline that produces plausible-looking garbage."""
    if not EMB_META.exists():
        raise SystemExit("no embedding cache — run 02_embed.py first")
    meta = json.loads(EMB_META.read_text(encoding="utf-8"))
    if meta.get("model") != MODEL:
        raise SystemExit(f"cache was built with {meta.get('model')}, code wants {MODEL}\n"
                         f"re-run 02_embed.py --force (changing the model voids every vector)")
    title = np.load(EMB_TITLE)
    ids = meta["ids"]
    if len(ids) != title.shape[0]:
        raise SystemExit("cache shapes disagree — re-run 02_embed.py --force")
    if offers is not None and [o["id"] for o in offers] != ids:
        raise SystemExit(f"offers_db.jsonl changed since the cache was built "
                         f"({len(offers)} rows vs {len(ids)} cached) — re-run 02_embed.py")
    return Cache(ids, title, meta)
