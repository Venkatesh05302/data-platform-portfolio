"""
01_setup_schema.py — Create the pgvector schema for Lab 02.

Why this file exists (Staff-engineer lens):
  Schema is the contract between producer (02_load_data.py) and consumers
  (03_search.py, 04_evaluate.py). Keep it explicit and versioned in a script,
  not as ad-hoc psql statements. In production this becomes a migration.

Run:
    python src/01_setup_schema.py
"""

from __future__ import annotations

import psycopg
from pgvector.psycopg import register_vector

# --- Config ---------------------------------------------------------------
# These match docker-compose.yml. In production, load from env vars, not code.
DB_DSN = "postgresql://labuser:labpass@localhost:5433/labdb"

# Lab 01 used sentence-transformers/all-MiniLM-L6-v2 → 384-dim vectors.
# If you swap models, this number changes; don't hardcode elsewhere.
EMBEDDING_DIM = 384


def main() -> None:
    with psycopg.connect(DB_DSN, autocommit=True) as conn:
        # Register the pgvector type adapter so we can pass numpy arrays directly
        register_vector(conn)

        with conn.cursor() as cur:
            # Ensure extension exists (idempotent — safe to re-run)
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # Drop and recreate for clean lab runs.
            # In production you'd migrate, not drop.
            cur.execute("DROP TABLE IF EXISTS chunks;")

            cur.execute(f"""
                CREATE TABLE chunks (
                    id           BIGSERIAL PRIMARY KEY,
                    chunk_id     TEXT UNIQUE NOT NULL,
                    doc_id       TEXT NOT NULL,
                    chunk_index  INT NOT NULL,
                    topic        TEXT NOT NULL,
                    text         TEXT NOT NULL,
                    embedding    vector({EMBEDDING_DIM}) NOT NULL
                );
            """)

            # HNSW index for approximate nearest neighbor search.
            # `vector_cosine_ops` = distance operator <=> which returns
            # (1 - cosine_similarity). We invert at query time to rank.
            cur.execute("""
                CREATE INDEX chunks_embedding_hnsw
                ON chunks
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """)

            # Regular btree index on topic for the metadata filter demo later.
            cur.execute("CREATE INDEX chunks_topic_idx ON chunks(topic);")

    print("✓ Schema ready: chunks table + HNSW index + topic index")


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# STRETCH:
#   1. Try IVFFlat instead of HNSW. Compare index build time and recall.
#   2. Add a `created_at TIMESTAMPTZ DEFAULT NOW()` column and index it —
#      lets you serve "recent docs only" queries.
#   3. Add a partial index on `WHERE topic = 'sql'` — pgvector supports
#      filtered indexes.
# ---------------------------------------------------------------------------
