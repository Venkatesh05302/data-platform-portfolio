"""
04_evaluate.py — Evaluate pgvector on Lab 01's 15 labeled queries.

Metric definitions (must match Lab 01 to compare):
  - recall@k: fraction of queries where any relevant doc appears in top-k
  - MRR:      mean reciprocal rank of the FIRST relevant doc found

Doc-level, not chunk-level. Multiple chunks may map to the same doc — we
dedupe by doc_id in the top-k list before scoring. Rationale: from a user's
perspective, "did we serve them a useful DOC?" not "did we serve them a
useful chunk?".

Off-topic queries (relevant_doc_ids = []) are excluded from the aggregate —
they exist to test failure behavior, not to score.

Run:
    python src/04_evaluate.py
"""

from __future__ import annotations

import json
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

# --- Config ---------------------------------------------------------------
HERE = Path(__file__).resolve().parent
LAB02_ROOT = HERE.parent
LAB01_DATA = LAB02_ROOT.parent / "01-embeddings-semantic-search" / "data"
EVAL_PATH = LAB01_DATA / "eval_queries.jsonl"

DB_DSN = "postgresql://labuser:labpass@localhost:5433/labdb"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Retrieve more than K chunks so we have room to dedupe to K unique docs
K_VALUES = [1, 3, 10]
RETRIEVE_MULTIPLIER = 4


def retrieve_docs(cur, q_vec, retrieve_n: int) -> list[str]:
    """Return top-N unique doc_ids ranked by similarity."""
    cur.execute(
        """
        SELECT doc_id
        FROM chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """,
        (q_vec, retrieve_n),
    )
    seen = []
    for (doc_id,) in cur.fetchall():
        if doc_id not in seen:
            seen.append(doc_id)
    return seen


def main() -> None:
    # Load queries
    queries = []
    with EVAL_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))

    print(f"Loaded {len(queries)} eval queries")

    scoring_queries = [q for q in queries if q.get("relevant_doc_ids")]
    off_topic_queries = [q for q in queries if not q.get("relevant_doc_ids")]
    print(
        f"  Scoring: {len(scoring_queries)}   Off-topic (excluded): {len(off_topic_queries)}\n"
    )

    model = SentenceTransformer(MODEL_NAME)

    # Accumulators
    hits = {k: 0 for k in K_VALUES}
    reciprocal_ranks = []  # for MRR

    max_k = max(K_VALUES)
    retrieve_n = max_k * RETRIEVE_MULTIPLIER

    with psycopg.connect(DB_DSN) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            for q in scoring_queries:
                q_vec = model.encode([q["query"]], normalize_embeddings=True)[0]
                relevant = set(q["relevant_doc_ids"])

                top_docs = retrieve_docs(cur, q_vec, retrieve_n)

                # recall@k for each k
                for k in K_VALUES:
                    if any(d in relevant for d in top_docs[:k]):
                        hits[k] += 1

                # MRR — reciprocal of the rank of first relevant doc found
                rr = 0.0
                for rank, d in enumerate(top_docs[:max_k], start=1):
                    if d in relevant:
                        rr = 1.0 / rank
                        break
                reciprocal_ranks.append(rr)

    n = len(scoring_queries)
    print(f"=== pgvector eval ({n} queries) ===\n")
    for k in K_VALUES:
        print(f"  recall@{k:<3d} = {hits[k] / n:.3f}   ({hits[k]}/{n})")
    print(f"  MRR       = {sum(reciprocal_ranks) / n:.3f}")

    print(
        "\nCompare to Lab 01 FAISS baseline (from learning-notes/lab-01-run-log.txt)."
    )
    print("Equivalent or nearly-equivalent numbers = pgvector is a valid replacement,")
    print("with the added feature of native metadata filtering.")


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# STRETCH:
#   1. Set hnsw.ef_search = 40 before searches → higher recall, slower.
#      Measure the trade-off with the same eval.
#   2. Try IVFFlat instead of HNSW: how does recall change?
#   3. Add a "filtered eval" — restrict each query to the topic of its
#      relevant docs and rerun. Recall should stay high (topic is a
#      correct filter); this proves pre-filter doesn't wreck quality.
# ---------------------------------------------------------------------------
