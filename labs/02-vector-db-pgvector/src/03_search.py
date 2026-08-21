"""
03_search.py — Search pgvector for top-K similar chunks.

Two modes:
  1. Pure vector search — same behavior as Lab 01's FAISS search
  2. Metadata pre-filter — restrict to a topic before searching
     (the feature FAISS doesn't have natively)

Concept — pre-filter vs post-filter:
  Pre-filter: WHERE topic = 'sql' AND then vector search.
  Postgres pushes the topic filter into the HNSW traversal — the graph
  only walks nodes matching the predicate. This is fast when the filter
  is not too selective. When it IS very selective (<1% of rows), HNSW
  can degrade because there aren't enough neighbors matching the filter
  in each hop. That's an SD interview trap worth knowing about.

Run:
    python src/03_search.py "how does spark handle skew"
    python src/03_search.py "SCD type 2" --topic dimensional-modeling --k 5
"""

from __future__ import annotations

import argparse

import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

# --- Config ---------------------------------------------------------------
DB_DSN = "postgresql://labuser:labpass@localhost:5433/labdb"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def search(
    query: str,
    k: int = 5,
    topic_filter: str | None = None,
) -> list[dict]:
    """Return top-K chunks ranked by cosine similarity."""
    model = SentenceTransformer(MODEL_NAME)
    q_vec = model.encode([query], normalize_embeddings=True)[0]

    # Build SQL depending on whether we're filtering
    # `<=>` is cosine distance in pgvector; smaller = more similar
    # We ORDER BY it ascending and select LIMIT k
    if topic_filter:
        sql = """
            SELECT chunk_id, doc_id, topic, text,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM chunks
            WHERE topic = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """
        params = (q_vec, topic_filter, q_vec, k)
    else:
        sql = """
            SELECT chunk_id, doc_id, topic, text,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """
        params = (q_vec, q_vec, k)

    with psycopg.connect(DB_DSN) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return [
        {
            "chunk_id": r[0],
            "doc_id": r[1],
            "topic": r[2],
            "text": r[3],
            "similarity": float(r[4]),
        }
        for r in rows
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="natural-language query")
    ap.add_argument("--k", type=int, default=5, help="top-K results")
    ap.add_argument("--topic", default=None, help="restrict to a specific topic")
    args = ap.parse_args()

    results = search(args.query, k=args.k, topic_filter=args.topic)

    print(f"\nQuery: {args.query}")
    if args.topic:
        print(f"Filter: topic = '{args.topic}'")
    print(f"Top {len(results)} results:\n")

    for i, r in enumerate(results, 1):
        print(
            f"[{i}] score={r['similarity']:.3f}  topic={r['topic']:15s}  doc={r['doc_id']}"
        )
        print(f"    {r['text'][:120]}...")
        print()


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# STRETCH:
#   1. EXPLAIN ANALYZE the two SQL paths — see the HNSW plan with/without filter.
#   2. Set hnsw.ef_search = 40 (higher recall, slower). Compare eval numbers.
#   3. Add multiple topic filters (WHERE topic IN (...)) and observe query plan.
# ---------------------------------------------------------------------------
