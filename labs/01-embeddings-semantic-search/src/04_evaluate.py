"""
04_evaluate.py — Evaluate retrieval quality with recall@k and MRR.

This is the script every RAG tutorial should include and almost none do.

Metric definitions:
  recall@k
    Of the ground-truth relevant docs for a query, what fraction appeared in
    the top-k retrieved results? Averaged over all queries.

    We compute recall at the *doc* level, not the chunk level: a query is
    considered served if any chunk from a relevant doc surfaces in top-k.

  MRR (Mean Reciprocal Rank)
    For each query, take the rank of the first relevant result (or 0 if none
    appears). Average 1/rank across queries. Rewards putting a relevant
    result *first*, not just eventually.

Interview lens:
  A Staff engineer will ask two questions when you claim your RAG "works well":
    1. Compared to what? (Baseline. Usually BM25.)
    2. On what data? (Labeled queries with ground-truth relevance.)
  This script is the answer to (2) and sets you up for (1) via 05_hybrid.py.

Run:
    python src/04_evaluate.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LAB_ROOT = HERE.parent
INDEX_PATH = LAB_ROOT / "data" / "vectors.faiss"
META_PATH = LAB_ROOT / "data" / "meta.parquet"
QUERIES_PATH = LAB_ROOT / "data" / "eval_queries.jsonl"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
K_VALUES = (1, 3, 10)


def load_eval_queries(path: Path) -> List[Dict]:
    queries = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))
    return queries


def retrieve_doc_ranks(query: str, k: int, index, meta: pd.DataFrame, model) -> List[str]:
    """Return the ordered list of unique doc_ids in the top-k results,
    de-duplicating multiple chunks from the same doc."""
    # Retrieve more chunks than k in case one doc dominates top hits.
    chunk_k = max(k * 4, 20)
    q_vec = model.encode(
        [query], normalize_embeddings=True, convert_to_numpy=True
    ).astype(np.float32, copy=False)
    _, ids = index.search(q_vec, chunk_k)
    seen: List[str] = []
    for vec_id in ids[0]:
        if vec_id < 0:
            continue
        doc_id = meta.iloc[int(vec_id)]["doc_id"]
        if doc_id not in seen:
            seen.append(doc_id)
        if len(seen) >= k:
            break
    return seen


def score_query(retrieved: List[str], relevant: List[str], k_values=K_VALUES):
    """Return per-k recall and reciprocal rank."""
    rel = set(relevant)
    out = {}
    for k in k_values:
        top_k = retrieved[:k]
        hit = sum(1 for d in top_k if d in rel)
        # recall is undefined when there are no relevant docs; report NaN and
        # exclude the query from the average.
        out[f"recall@{k}"] = float(hit) / len(rel) if rel else float("nan")

    rr = 0.0
    for i, d in enumerate(retrieved, start=1):
        if d in rel:
            rr = 1.0 / i
            break
    out["rr"] = rr if rel else float("nan")
    return out


def main():
    import faiss
    from sentence_transformers import SentenceTransformer

    index = faiss.read_index(str(INDEX_PATH))
    meta = pd.read_parquet(META_PATH)
    model = SentenceTransformer(MODEL_NAME)

    queries = load_eval_queries(QUERIES_PATH)
    print(f"Evaluating {len(queries)} queries against {len(meta)} chunks ({meta['doc_id'].nunique()} docs)\n")

    rows = []
    for q in queries:
        retrieved = retrieve_doc_ranks(q["query"], max(K_VALUES), index, meta, model)
        scored = score_query(retrieved, q["relevant_doc_ids"])
        rows.append({
            "query_id": q["query_id"],
            "query": q["query"],
            "n_relevant": len(q["relevant_doc_ids"]),
            "top_docs": " > ".join(retrieved[:5]),
            **scored,
        })

    df = pd.DataFrame(rows)

    # Per-query view
    with pd.option_context("display.max_colwidth", 80, "display.width", 200):
        cols = ["query_id", "query", "n_relevant", "recall@1", "recall@3", "recall@10", "rr", "top_docs"]
        print(df[cols].to_string(index=False))

    # Aggregate (skipping queries with no relevant docs — the "dinner" case)
    scored_only = df.dropna(subset=["recall@1"])
    print("\n=== Aggregate (pure vector) ===")
    print(f"Queries scored: {len(scored_only)} / {len(df)}")
    for k in K_VALUES:
        print(f"  recall@{k}: {scored_only[f'recall@{k}'].mean():.3f}")
    print(f"  MRR:      {scored_only['rr'].mean():.3f}")

    # Highlight the deliberate off-topic query
    off_topic = df[df["n_relevant"] == 0]
    if not off_topic.empty:
        print("\n=== Off-topic query (no ground truth) ===")
        for _, r in off_topic.iterrows():
            print(f"  {r['query_id']}: {r['query']}")
            print(f"    top docs: {r['top_docs']}")
        print("  In production, wire a min-score threshold to catch this class of query.")


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# Interpretation guide:
#   recall@3 above 0.75 → strong retrieval on this corpus.
#   recall@3 between 0.5 and 0.75 → typical, room to improve via chunking.
#   recall@3 below 0.5 → chunking or model is fighting you; investigate.
#
# The gap between recall@1 and recall@3 tells you whether the right answer is
# consistently first or merely nearby. Bigger gap = re-ranking would help.
# ---------------------------------------------------------------------------
