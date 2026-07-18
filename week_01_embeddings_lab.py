"""
Week 1 Lab: Embeddings — Senior DE Edition
==========================================

Goal: Build the muscle for thinking about embeddings as a DE problem,
not just an ML one.

Run this script, then complete the four "STRETCH" challenges at the bottom.
Total time: 90-120 minutes.

Setup:
  pip install openai numpy scikit-learn python-dotenv --break-system-packages
  export OPENAI_API_KEY="sk-..."   # or put in .env file (gitignored!)

If you don't have an OpenAI API key:
  - Use the sentence-transformers fallback (set USE_LOCAL=True below).
  - First run: pip install sentence-transformers --break-system-packages
  - Quality is similar enough for learning purposes.
"""

import os
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import List, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
USE_LOCAL = False            # Set True to use sentence-transformers (no API key needed)
MODEL_ID = "text-embedding-3-small"
MODEL_VERSION = "v1"         # Use this to mark embeddings — critical for migration later
EMBEDDING_DIM = 1536         # Default for text-embedding-3-small; supports truncation

# ---------------------------------------------------------------------------
# Step 1: A tiny domain corpus
# We use 4 clusters of meaning so cluster separation is testable.
# ---------------------------------------------------------------------------
CORPUS = [
    # Cluster A: ETL pipeline failures
    "The nightly ETL job failed because the source database timed out.",
    "Our pipeline broke when the upstream API returned 503 errors.",
    "Glue job failed with an OOM error during the transformation step.",
    "Airflow DAG failed because a sensor task timed out waiting for the file.",
    "The Spark job crashed when it encountered a corrupt Parquet file.",

    # Cluster B: Customer churn analytics
    "We saw a 12% spike in customer churn last quarter.",
    "Users who don't log in within 7 days have 3x higher churn.",
    "Churn correlates strongly with the number of failed payment attempts.",
    "Cohort analysis shows our Q3 signups churn faster than Q2.",
    "Churn predictions improved when we added support-ticket features.",

    # Cluster C: Data warehouse cost optimization
    "Snowflake credits dropped 30% after we right-sized warehouses.",
    "We reduced Redshift costs by switching to RA3 nodes.",
    "BigQuery slot reservations saved us money on predictable workloads.",
    "Compacting Iceberg tables cut our S3 storage cost in half.",
    "Killing idle warehouses during off-hours reduced compute spend.",

    # Cluster D: System design / architecture
    "We chose Kafka over Kinesis for higher throughput per partition.",
    "Medallion architecture made it easier to reason about data quality.",
    "We migrated from Lambda architecture to Kappa for simplicity.",
    "CDC with Debezium gave us near-real-time analytics.",
    "Data Mesh worked because our domains had strong ownership.",
]

LABELS = (
    ["etl_failure"] * 5
    + ["churn"] * 5
    + ["cost"] * 5
    + ["architecture"] * 5
)


# ---------------------------------------------------------------------------
# Step 2: The embedding function
# Notice the DE concerns wrapped around it: hashing, versioning, retries.
# ---------------------------------------------------------------------------
def content_hash(text: str) -> str:
    """Stable hash of the input. Use this as part of your primary key
    in production so you never re-embed identical content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def embed_openai(texts: List[str]) -> np.ndarray:
    from openai import OpenAI
    client = OpenAI()
    # In prod: wrap in retry-with-backoff; here we keep it simple.
    resp = client.embeddings.create(model=MODEL_ID, input=texts)
    return np.array([d.embedding for d in resp.data], dtype=np.float32)


def embed_local(texts: List[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return np.array(model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def embed(texts: List[str]) -> np.ndarray:
    return embed_local(texts) if USE_LOCAL else embed_openai(texts)


# ---------------------------------------------------------------------------
# Step 3: Build an "embedding record" — this is the shape you'd actually
# write to your vector store. Stored as JSON Lines for inspection.
# ---------------------------------------------------------------------------
def make_records(texts: List[str], vectors: np.ndarray, labels: List[str]) -> List[dict]:
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "id": content_hash(t),
            "text": t,
            "label": labels[i],
            "model_id": MODEL_ID if not USE_LOCAL else "all-MiniLM-L6-v2",
            "model_version": MODEL_VERSION,
            "dim": int(vectors.shape[1]),
            "embedded_at": now,
            # vector is heavy; we don't write it to JSON here, just inspect shape
        }
        for i, t in enumerate(texts)
    ]


# ---------------------------------------------------------------------------
# Step 4: Build a similarity matrix and inspect clustering
# ---------------------------------------------------------------------------
def show_similarity_matrix(vectors: np.ndarray, labels: List[str]) -> np.ndarray:
    sim = cosine_similarity(vectors)
    print("\n=== Pairwise cosine similarity (first 5 rows, first 5 cols) ===")
    print("Labels:", labels[:5])
    print(np.round(sim[:5, :5], 3))
    return sim


def cluster_separation_score(sim: np.ndarray, labels: List[str]) -> float:
    """Average intra-cluster similarity minus average inter-cluster similarity.
    Higher = better separation. This is your 'is the embedding model
    actually useful for my data?' metric. In production this drives
    model-selection decisions."""
    labels_arr = np.array(labels)
    intra, inter = [], []
    for i in range(len(labels_arr)):
        for j in range(i + 1, len(labels_arr)):
            if labels_arr[i] == labels_arr[j]:
                intra.append(sim[i, j])
            else:
                inter.append(sim[i, j])
    return float(np.mean(intra) - np.mean(inter))


# ---------------------------------------------------------------------------
# Step 5: Query the corpus — this is RAG retrieval in 4 lines
# ---------------------------------------------------------------------------
def retrieve(query: str, vectors: np.ndarray, texts: List[str], top_k: int = 3) -> List[Tuple[str, float]]:
    q_vec = embed([query])
    sims = cosine_similarity(q_vec, vectors)[0]
    top_idx = np.argsort(sims)[::-1][:top_k]
    return [(texts[i], float(sims[i])) for i in top_idx]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Embedding {len(CORPUS)} sentences with model={MODEL_ID} (local={USE_LOCAL})")
    t0 = time.time()
    vectors = embed(CORPUS)
    print(f"Embedded in {time.time() - t0:.2f}s — shape: {vectors.shape}")

    records = make_records(CORPUS, vectors, LABELS)
    print("\n=== Sample record (vector omitted) ===")
    print(json.dumps(records[0], indent=2))

    sim = show_similarity_matrix(vectors, LABELS)
    score = cluster_separation_score(sim, LABELS)
    print(f"\nCluster separation score: {score:.3f}")
    print("(Above ~0.20 is decent. Above ~0.35 is strong. Below 0.10 means your model is wrong for this data.)")

    print("\n=== Retrieval test ===")
    for q in [
        "Why did the ETL job error last night?",
        "How can we save money on the data warehouse?",
        "Should we use Lambda or Kappa architecture?",
    ]:
        print(f"\nQuery: {q}")
        for text, score in retrieve(q, vectors, CORPUS, top_k=3):
            print(f"  [{score:.3f}] {text}")

# =============================================================================
# STRETCH CHALLENGES — these are the actual learning
# =============================================================================
# 1) Bad query failure mode:
#    Add a query like "what time is dinner?" — what gets retrieved? Why?
#    Most RAG systems naively return the top-3 even when nothing matches.
#    How would you handle this in production? (Hint: similarity threshold.)
#
# 2) Embedding the wrong thing:
#    Add a paragraph of raw HTML/markdown like:
#       "<div class='alert'>**Pipeline FAILED!** See [logs](url) for details.</div>"
#    Embed it alongside the clean version. Compare similarity to the
#    cluster of failure sentences. Conclusion?
#
# 3) Re-embed determinism:
#    Run the script twice with the SAME corpus. Are the vectors identical?
#    Now change ONE word in one sentence. How many similarity values shift?
#    (This is why content_hash matters for caching.)
#
# 4) Cost calculator (the DE part):
#    text-embedding-3-small costs $0.02 / 1M tokens.
#    Estimate: cost to embed 100M support tickets, average 200 tokens each.
#    Now: what if you re-embed when the model deprecates? Annual cost
#    if model deprecates every 18 months and you have 1B documents?
#    (Write your answer in your reflection doc.)
