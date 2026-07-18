"""
03_search.py — Interactive semantic search CLI.

Usage:
    python src/03_search.py                       # interactive mode
    python src/03_search.py "your query here"     # one-shot mode
    python src/03_search.py --k 5 "your query"    # top-5

Watch the *scores*, not just the ranks. In production, a similarity threshold
(e.g., "if top score < 0.35, respond 'I don't know'") is the difference between
a system that admits ignorance and one that hallucinates confidently.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LAB_ROOT = HERE.parent
INDEX_PATH = LAB_ROOT / "data" / "vectors.faiss"
META_PATH = LAB_ROOT / "data" / "meta.parquet"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_all():
    import faiss
    if not INDEX_PATH.exists() or not META_PATH.exists():
        raise SystemExit("index/meta missing — run 02_embed_index.py first")
    index = faiss.read_index(str(INDEX_PATH))
    meta = pd.read_parquet(META_PATH)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    return index, meta, model


def search(query: str, index, meta: pd.DataFrame, model, k: int = 3):
    q_vec = model.encode(
        [query], normalize_embeddings=True, convert_to_numpy=True
    ).astype(np.float32, copy=False)
    scores, ids = index.search(q_vec, k)
    scores, ids = scores[0], ids[0]
    hits = []
    for score, vec_id in zip(scores, ids):
        if vec_id < 0:
            continue
        row = meta.iloc[int(vec_id)]
        hits.append({
            "score": float(score),
            "doc_id": row["doc_id"],
            "topic": row["topic"],
            "chunk_id": row["chunk_id"],
            "text": row["text"],
        })
    return hits


def print_hits(query: str, hits):
    print(f"\nQuery: {query}")
    if not hits:
        print("  (no results)")
        return
    for i, h in enumerate(hits, 1):
        print(f"  {i}. [score={h['score']:.3f}] {h['doc_id']} ({h['topic']})")
        text = h["text"].replace("\n", " ")
        if len(text) > 160:
            text = text[:157] + "..."
        print(f"       {text}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="*", help="query (omit for interactive mode)")
    parser.add_argument("--k", type=int, default=3, help="top-k")
    args = parser.parse_args()

    index, meta, model = load_all()

    if args.query:
        query = " ".join(args.query)
        print_hits(query, search(query, index, meta, model, k=args.k))
        return

    print("Interactive mode. Ctrl-D or Ctrl-C to quit.\n")
    try:
        while True:
            try:
                query = input("query> ").strip()
            except EOFError:
                print()
                break
            if not query:
                continue
            print_hits(query, search(query, index, meta, model, k=args.k))
            print()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# Try these queries and reason about the scores:
#   what causes shuffle skew?
#   how do we cut redshift costs?
#   explain data mesh
#   what time is dinner            ← should return low-score results
#
# The last one is the failure mode most tutorials never show you.
# ---------------------------------------------------------------------------
