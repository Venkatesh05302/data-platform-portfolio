"""
02_load_data.py — Load Lab 01 embeddings into pgvector.

Why this file exists:
  Bulk-loading vectors is the moment where you learn how expensive inserts
  are. Naive INSERT-one-at-a-time is 100x slower than batch insert. In
  production this becomes a COPY FROM. Here we use psycopg's executemany
  which is a good middle ground for lab scale.

Reads:
    labs/01-embeddings-semantic-search/data/vectors.npy    (148 × 384 float32)
    labs/01-embeddings-semantic-search/data/meta.parquet   (148 rows metadata)

Writes:
    chunks table (148 rows)

Run:
    python src/02_load_data.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import psycopg
from pgvector.psycopg import register_vector
from tqdm import tqdm

# --- Config ---------------------------------------------------------------
HERE = Path(__file__).resolve().parent
LAB02_ROOT = HERE.parent
LAB01_DATA = LAB02_ROOT.parent / "01-embeddings-semantic-search" / "data"

VECTORS_PATH = LAB01_DATA / "vectors.npy"
META_PATH = LAB01_DATA / "meta.parquet"

DB_DSN = "postgresql://labuser:labpass@localhost:5433/labdb"
BATCH_SIZE = 64  # tuning knob — bigger = fewer round trips, more memory


def main() -> None:
    # --- Load Lab 01 outputs -----------------------------------------------
    if not VECTORS_PATH.exists():
        raise SystemExit(f"vectors not found at {VECTORS_PATH} — run Lab 01 first")

    vectors = np.load(VECTORS_PATH)  # shape: (148, 384) float32
    meta = pd.read_parquet(META_PATH)  # 148 rows

    n_vectors, dim = vectors.shape
    assert n_vectors == len(meta), (
        f"positional alignment broken: {n_vectors} vectors vs {len(meta)} meta rows"
    )
    print(f"Loaded {n_vectors} vectors × {dim} dims from Lab 01")
    print(f"Meta columns: {list(meta.columns)}")

    # --- Prepare rows for insert ------------------------------------------
    # meta.parquet columns from Lab 01: chunk_id, doc_id, chunk_index, topic, text
    rows = [
        (
            meta.iloc[i]["chunk_id"],
            meta.iloc[i]["doc_id"],
            int(meta.iloc[i]["chunk_index"]),
            meta.iloc[i]["topic"],
            meta.iloc[i]["text"],
            vectors[i],  # numpy array — pgvector adapter handles conversion
        )
        for i in range(n_vectors)
    ]

    # --- Bulk insert ------------------------------------------------------
    with psycopg.connect(DB_DSN) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            # Wipe existing rows for clean re-runs (lab convenience only)
            cur.execute("TRUNCATE TABLE chunks RESTART IDENTITY;")

            # executemany with batch — psycopg batches these internally
            for start in tqdm(
                range(0, len(rows), BATCH_SIZE), desc="Inserting batches"
            ):
                batch = rows[start : start + BATCH_SIZE]
                cur.executemany(
                    """
                    INSERT INTO chunks (chunk_id, doc_id, chunk_index, topic, text, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    batch,
                )
        conn.commit()

    # --- Verify ------------------------------------------------------------
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM chunks;")
            count = cur.fetchone()[0]
            cur.execute(
                "SELECT topic, COUNT(*) FROM chunks GROUP BY topic ORDER BY 2 DESC;"
            )
            topic_counts = cur.fetchall()

    print(f"\n✓ Loaded {count} rows into chunks")
    print(f"\nTop topics:")
    for topic, n in topic_counts:
        print(f"  {topic:20s} {n}")


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# STRETCH:
#   1. Replace executemany with COPY FROM STDIN — 10x faster for large loads.
#   2. Add ON CONFLICT (chunk_id) DO UPDATE to make this idempotent for
#      re-embeds (content-hash chunk_ids won't collide unless text is identical).
#   3. Time the load; try BATCH_SIZE = 1, 16, 64, 256 — plot the tradeoff.
# ---------------------------------------------------------------------------
