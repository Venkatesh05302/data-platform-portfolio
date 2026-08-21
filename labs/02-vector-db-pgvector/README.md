# Lab 02 — Vector Search with pgvector

Level up from Lab 01's in-memory FAISS to a **real vector database** running as a Postgres extension. Same corpus, same queries — but now with persistent storage, metadata filtering, and the operational shape of a production vector store.

## Why pgvector (vs. Pinecone/Qdrant/Weaviate)

Most enterprises reach for pgvector before dedicated vector DBs because:

1. **Zero new infra to manage** — vectors live inside existing Postgres
2. **Same transactional semantics** as the rest of the app — ACID inserts, atomic joins with metadata tables
3. **Metadata filtering is a WHERE clause** — no separate metadata index to keep in sync
4. **Cost curve** — a t3.medium Postgres handles 10M vectors before you outgrow it; only then do you need a dedicated vector DB

**When pgvector runs out:** ~50M+ vectors, or when HNSW rebuild cost during large ingests dominates ops burden. Then you migrate to Pinecone/Qdrant.

## Architecture

```
Lab 01 outputs                     Lab 02 (this lab)
─────────────────                  ────────────────────
vectors.npy       ────────────▶    Docker: pgvector/pgvector:pg16
meta.parquet                              │
                                          ▼
                                   chunks table
                                   ├── chunk_id, doc_id, topic, text
                                   ├── embedding vector(384)
                                   └── HNSW index (cosine)

                                   Query flow:
                                     query → embed (MiniLM)
                                          → SELECT ... ORDER BY embedding <=> $1
                                          → top-K rows with metadata + similarity
```

## Setup

```bash
# 1. Start Postgres + pgvector
docker compose up -d

# 2. Verify (optional)
docker compose ps
docker exec -it lab02-pgvector psql -U labuser -d labdb -c '\dx'
# Should list the `vector` extension

# 3. Python env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Pipeline

Each script is independently runnable; downstream scripts assume upstream has completed.

```bash
python src/01_setup_schema.py    # create table + HNSW index + btree on topic
python src/02_load_data.py       # bulk-insert Lab 01 vectors into chunks
python src/03_search.py "..."    # CLI: semantic search with optional --topic filter
python src/04_evaluate.py        # recall@k + MRR on Lab 01's eval queries
```

## Results

pgvector on the same 15 labeled queries as Lab 01:

| Metric | pgvector (HNSW, cosine) |
|--------|-------------------------|
| recall@1 | 0.857 (12/14) |
| recall@3 | **1.000** (14/14) |
| recall@10 | 1.000 (14/14) |
| MRR | 0.929 |

Interpretation: **retrieval quality is not the bottleneck.** Top-3 is 100%. Any product built on this retriever should focus improvements on ranking (rerankers) or LLM generation, not on retrieval recall.

## The Feature FAISS Doesn't Have — Metadata Pre-filtering

Same query, unfiltered vs. filtered:

```bash
$ python src/03_search.py "how do we handle late arrivals" --k 3
# Returns a mix of streaming, SCD, and Kafka results

$ python src/03_search.py "how do we handle late arrivals" --topic kafka_streaming --k 3
# All 3 results guaranteed from kafka_streaming; similarity scores lower
# because we forced the top-K within a subset
```

**How pgvector does it:** the `WHERE topic = 'kafka_streaming'` predicate is pushed into the HNSW traversal — the graph only walks nodes matching the filter. This is called **pre-filtering** (as opposed to post-filtering: search everything, then drop non-matches).

**When pre-filtering hurts:** if the filter is very selective (<1% of rows match), HNSW's graph doesn't have enough authorized neighbors per hop and recall degrades. At that point you switch to partitioned indexes (one HNSW per tenant/topic) or over-fetch and post-filter.

## Interview-Relevant Concepts Touched

- **HNSW** — approximate nearest-neighbor graph. `m=16`, `ef_construction=64` are the standard build-time knobs.
- **Distance operators** — `<->` (L2), `<#>` (negative inner product), `<=>` (cosine). Lab 01's L2-normalized vectors work seamlessly with `<=>`.
- **Pre-filter vs post-filter** — real design trade-off. Pre-filter is faster but degrades HNSW recall under high selectivity.
- **Approximate ≠ wrong** — HNSW is approximate. Recall at 71 docs is essentially exact; at 10M docs you set `ef_search` higher to trade latency for recall.
- **Bulk insert patterns** — naive `INSERT` in a loop is 100x slower than `executemany`, which is 10x slower than `COPY FROM STDIN`. Choose based on scale.

## What's Deliberately Missing (Stretch Goals)

- **`COPY FROM STDIN` for load** — would be 10x faster at 10M+ rows
- **`hnsw.ef_search` tuning** — measure the recall/latency curve
- **IVFFlat vs HNSW comparison** — different index types, different trade-offs
- **Idempotent load** — `ON CONFLICT (chunk_id) DO UPDATE` for re-embed migrations
- **Backup/restore** — pg_dump the chunks table + volume backup
- **Multi-tenant partitioning** — one HNSW per tenant when ACL filter selectivity is very high

## Files

```
labs/02-vector-db-pgvector/
├── README.md                    (this file)
├── docker-compose.yml           (Postgres + pgvector)
├── requirements.txt             (psycopg, pgvector, sentence-transformers)
└── src/
    ├── 01_setup_schema.py       (chunks table + HNSW + topic index)
    ├── 02_load_data.py          (Lab 01 vectors → chunks table)
    ├── 03_search.py             (search CLI with --topic filter)
    └── 04_evaluate.py           (recall@k + MRR)
```
