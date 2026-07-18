"""
05_hybrid.py — Hybrid retrieval: BM25 + vector, fused with Reciprocal Rank
Fusion (RRF), evaluated with the same recall@k harness as 04.

Why hybrid:
  Pure vector search is strong on paraphrase and semantically related terms
  but weak on rare tokens — product codes, error identifiers, proper nouns,
  version numbers, acronyms. BM25 is the opposite: strong on exact tokens,
  weak on paraphrase. Combining them beats either alone on almost every
  real-world corpus.

Reciprocal Rank Fusion:
  RRF(d) = Σ over rankers r of 1 / (k_rrf + rank_r(d))
  Where k_rrf is a small constant (60 is the canonical value). RRF is
  parameter-light, score-scale invariant, and empirically robust — no need
  to tune the weighting between BM25 scores and cosine scores, which live
  on different scales.

Run:
    python src/05_hybrid.py
"""

from __future__ import annotations

import json
import re
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
RRF_K = 60           # RRF smoothing constant
RETRIEVE_N = 30      # how many chunks each ranker returns before fusion


TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def load_eval_queries(path: Path) -> List[Dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def vector_rank(query: str, model, index, n: int) -> List[int]:
    """Return chunk indices for top-n by cosine."""
    q_vec = model.encode(
        [query], normalize_embeddings=True, convert_to_numpy=True
    ).astype(np.float32, copy=False)
    _, ids = index.search(q_vec, n)
    return [int(x) for x in ids[0] if x >= 0]


def bm25_rank(query: str, bm25, n: int) -> List[int]:
    scores = bm25.get_scores(tokenize(query))
    order = np.argsort(scores)[::-1][:n]
    return [int(i) for i in order]


def rrf_fuse(rankings: List[List[int]], k: int, k_rrf: int = RRF_K) -> List[int]:
    """Fuse multiple rankings by Reciprocal Rank Fusion, return top-k chunk ids."""
    score: Dict[int, float] = {}
    for ranking in rankings:
        for rank, chunk_idx in enumerate(ranking, start=1):
            score[chunk_idx] = score.get(chunk_idx, 0.0) + 1.0 / (k_rrf + rank)
    return [i for i, _ in sorted(score.items(), key=lambda kv: kv[1], reverse=True)[:k]]


def chunks_to_doc_ranks(chunk_ids: List[int], meta: pd.DataFrame, k: int) -> List[str]:
    seen: List[str] = []
    for vec_id in chunk_ids:
        doc_id = meta.iloc[vec_id]["doc_id"]
        if doc_id not in seen:
            seen.append(doc_id)
        if len(seen) >= k:
            break
    return seen


def score_query(retrieved: List[str], relevant: List[str]):
    rel = set(relevant)
    out = {}
    for k in K_VALUES:
        top_k = retrieved[:k]
        hit = sum(1 for d in top_k if d in rel)
        out[f"recall@{k}"] = float(hit) / len(rel) if rel else float("nan")
    rr = 0.0
    for i, d in enumerate(retrieved, start=1):
        if d in rel:
            rr = 1.0 / i
            break
    out["rr"] = rr if rel else float("nan")
    return out


def print_aggregate(name: str, df: pd.DataFrame):
    scored = df.dropna(subset=["recall@1"])
    print(f"\n=== {name} ===")
    print(f"Queries scored: {len(scored)} / {len(df)}")
    for k in K_VALUES:
        print(f"  recall@{k}: {scored[f'recall@{k}'].mean():.3f}")
    print(f"  MRR:      {scored['rr'].mean():.3f}")


def main():
    import faiss
    from rank_bm25 import BM25Okapi
    from sentence_transformers import SentenceTransformer

    index = faiss.read_index(str(INDEX_PATH))
    meta = pd.read_parquet(META_PATH).reset_index(drop=True)
    model = SentenceTransformer(MODEL_NAME)

    # Build BM25 over the same chunks that FAISS indexed. Order matters: the
    # BM25 index position must match the FAISS vec_id.
    tokenized_corpus = [tokenize(t) for t in meta["text"].tolist()]
    bm25 = BM25Okapi(tokenized_corpus)

    queries = load_eval_queries(QUERIES_PATH)
    print(f"Evaluating {len(queries)} queries — pure vector vs BM25 vs hybrid (RRF)\n")

    vec_rows, bm25_rows, hybrid_rows = [], [], []
    for q in queries:
        vec_ranking = vector_rank(q["query"], model, index, RETRIEVE_N)
        bm_ranking = bm25_rank(q["query"], bm25, RETRIEVE_N)
        hybrid_ranking = rrf_fuse([vec_ranking, bm_ranking], k=RETRIEVE_N)

        for ranking, out_rows in (
            (vec_ranking, vec_rows),
            (bm_ranking, bm25_rows),
            (hybrid_ranking, hybrid_rows),
        ):
            docs = chunks_to_doc_ranks(ranking, meta, max(K_VALUES))
            out_rows.append({
                "query_id": q["query_id"],
                "query": q["query"],
                "n_relevant": len(q["relevant_doc_ids"]),
                "top_docs": " > ".join(docs[:5]),
                **score_query(docs, q["relevant_doc_ids"]),
            })

    df_vec = pd.DataFrame(vec_rows)
    df_bm25 = pd.DataFrame(bm25_rows)
    df_hybrid = pd.DataFrame(hybrid_rows)

    # Per-query side-by-side
    joined = df_vec[["query_id", "query", "n_relevant"]].copy()
    for name, d in (("vec", df_vec), ("bm25", df_bm25), ("hybrid", df_hybrid)):
        joined[f"{name}_r@3"] = d["recall@3"]
        joined[f"{name}_rr"] = d["rr"]
    with pd.option_context("display.max_colwidth", 60, "display.width", 200):
        print(joined.to_string(index=False))

    print_aggregate("Pure vector", df_vec)
    print_aggregate("BM25", df_bm25)
    print_aggregate("Hybrid (RRF)", df_hybrid)

    print("\nRead the delta between pure vector and hybrid — that is the value")
    print("of hybrid retrieval on this corpus. Small deltas are common on very")
    print("clean corpora; big deltas show up when queries use exact terminology")
    print("or rare tokens that vector space blurs.")


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# STRETCH — implement a cross-encoder re-ranker:
#   1. Retrieve top-20 chunks with the hybrid pipeline.
#   2. Pass (query, chunk) pairs into a cross-encoder like
#      "cross-encoder/ms-marco-MiniLM-L-6-v2".
#   3. Re-sort by cross-encoder score; keep top-3.
#   4. Compare recall@3.
#
# Cross-encoders are slower (score every pair) but much more accurate. In
# production, retrieval fetches many candidates and a cross-encoder re-ranks
# the shortlist. This pattern is called "retrieve-and-rerank" and is what
# every serious RAG system uses.
# ---------------------------------------------------------------------------
