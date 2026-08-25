r"""Stage 0 checkpoint: load the model, report its real limits.

Run:  .venv\Scripts\python.exe finder\prototype\semantic\00_check.py

First run downloads ~470 MB into ~/.cache/huggingface. Later runs are offline and fast.
"""

import time

from sentence_transformers import SentenceTransformer

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

t0 = time.perf_counter()
model = SentenceTransformer(MODEL)
print(f"loaded in {time.perf_counter() - t0:.1f}s")

print(f"model            {MODEL}")
print(f"max_seq_length   {model.max_seq_length}   <- tokens; silent truncation past this")
print(f"output dims      {model.get_embedding_dimension()}")
print(f"device           {model.device}")

# Prove the pipeline end to end: two vectors, one cosine.
pair = ["Programista Python", "Python Developer"]
vecs = model.encode(pair, normalize_embeddings=True)
print(f"vector shape     {vecs.shape}  dtype={vecs.dtype}")
print(f"norm of vec[0]   {float((vecs[0] ** 2).sum()) ** 0.5:.4f}   <- 1.0 => dot == cosine")
print(f'cosine("{pair[0]}", "{pair[1]}") = {float(vecs[0] @ vecs[1]):.4f}')

# How many tokens do our real inputs actually cost?
print("\ntoken counts (vs max_seq_length above):")
for text in [
    "Python Developer",
    "Analityk biznesowy IT (Sektor Płatności / Acquiring & Processing)",
    "BigQuery, DBT, GraphQL, MySQL, Oracle, REST API, SQL Server, Snowflake",
]:
    n = len(model.tokenizer(text)["input_ids"])
    print(f"  {n:3d}  {text[:60]}")
