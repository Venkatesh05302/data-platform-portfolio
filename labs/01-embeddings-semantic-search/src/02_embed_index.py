"""
02_embed_index.py — Batch-embed chunks and build a FAISS index.

Why FAISS IndexFlatIP:
  - Flat = exact, brute-force search. No ANN approximation. For an 80-doc lab
    this is trivially fast and rules out "did ANN hurt recall?" as a variable.
  - IP = inner product. We L2-normalize embeddings, so inner product equals
    cosine similarity. This is the standard trick — do it once and never think
    about the difference again.

Real-world: for millions of vectors you switch to IndexIVFFlat, IndexIVFPQ, or
IndexHNSWFlat. Each trades recall for latency/memory in different ways. The
lab intentionally uses Flat so you learn the semantics before the tuning.

DE lens — this is the pattern the script demonstrates:
  1. Read chunks (deterministic input).
  2. Batch them into the model with a size that keeps GPU/CPU utilization high.
  3. Persist vectors in a format you can rebuild indexes from without re-calling
     the model — this is the entire reason a well-designed RAG pipeline
     separates "embed" from "index".
  4. Write a metadata sidecar so you can go vec_id → chunk_id → doc_id → topic.

Run:
    python src/02_embed_index.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LAB_ROOT = HERE.parent
CHUNKS_PATH = LAB_ROOT / "data" / "chunks.jsonl"
INDEX_PATH = LAB_ROOT / "data" / "vectors.faiss"
META_PATH = LAB_ROOT / "data" / "meta.parquet"
VECTORS_PATH = LAB_ROOT / "data" / "vectors.npy"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 32


def load_chunks(path: Path) -> pd.DataFrame:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if not rows:
        raise SystemExit(f"no chunks found at {path} — run 01_ingest_chunk.py first")
    return pd.DataFrame(rows)


def embed_all(texts: List[str], model_name: str, batch_size: int) -> np.ndarray:
    """Load model once, batch-encode all texts, return an (N, D) float32 matrix
    with L2-normalized rows so inner-product == cosine similarity."""
    # Lazy import so a failed dependency install doesn't blow up module load.
    from sentence_transformers import SentenceTransformer

    print(f"Loading model {model_name} (first run downloads ~90 MB)...")
    model = SentenceTransformer(model_name)
    print(f"Encoding {len(texts)} chunks (batch_size={batch_size})...")
    t0 = time.time()
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    ).astype(np.float32, copy=False)
    dt = time.time() - t0
    throughput = len(texts) / dt if dt > 0 else float("inf")
    print(f"Encoded in {dt:.2f}s — {throughput:.1f} chunks/sec — shape {vectors.shape}")
    return vectors


def build_faiss_index(vectors: np.ndarray):
    import faiss
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index


def main() -> None:
    df = load_chunks(CHUNKS_PATH)
    print(f"Chunks loaded: {len(df)}")

    vectors = embed_all(df["text"].tolist(), MODEL_NAME, BATCH_SIZE)

    # Persist raw vectors and metadata. Keeping vectors as a .npy lets us rebuild
    # any FAISS index variant without re-embedding — the expensive step.
    np.save(VECTORS_PATH, vectors)
    df.assign(vec_id=range(len(df))).to_parquet(META_PATH, index=False)

    index = build_faiss_index(vectors)
    import faiss
    faiss.write_index(index, str(INDEX_PATH))

    on_disk_bytes = vectors.nbytes
    print(f"Wrote {VECTORS_PATH.name} ({on_disk_bytes / 1024:.1f} KiB), "
          f"{META_PATH.name}, and {INDEX_PATH.name}")
    print(f"Vector footprint math: {vectors.shape[0]} × {vectors.shape[1]} × 4 bytes "
          f"= {on_disk_bytes} bytes")


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# STRETCH A — Content-hash caching (idempotence):
#   1. Load the existing meta.parquet at the top of main().
#   2. Skip chunks whose chunk_id is already in meta.
#   3. Only embed the new ones, append vectors, rebuild the index.
#   4. Prove idempotence: second run reports "0 new chunks to embed".
#
# STRETCH B — Model comparison:
#   Change MODEL_NAME to "BAAI/bge-small-en-v1.5" (same 384 dim, generally
#   stronger). Rerun 02 and 04. Log the recall delta.
# ---------------------------------------------------------------------------
