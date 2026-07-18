# Lab 01 — Semantic Search over a DE Corpus (Writeup)

**Lab:** `labs/01-embeddings-semantic-search`
**Corpus:** 71 short paragraphs across 8 DE topics (Spark, Delta/Iceberg, Kafka/streaming, warehouse cost, CDC, orchestration, data quality, system design). Avg 47 whitespace tokens/doc, range 36–63.
**Eval set:** 15 hand-labeled queries; 14 with ground truth, 1 deliberate off-topic (`q15: what time is dinner tonight`).
**Model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim, CPU).
**Index:** FAISS `IndexFlatIP` (exact search, cosine via L2-normalized inner product).
**Retrieval eval unit:** doc-level. A query is served if any chunk from a ground-truth doc surfaces in the top-k (chunks from the same doc are de-duplicated before scoring).

> How to reproduce every number below: `python src/06_capture_metrics.py`
> It sweeps two chunking configs, runs 01→02→04→05 for each, and writes
> `learning-notes/lab-01-run-log.txt`. Numbers in this writeup should match
> that log exactly.

---

## 1. Numbers

### Baseline (chunk_size=32 tokens, overlap=8)

| Metric | Value |
|---|---|
| Docs ingested | 71 |
| Chunks written | 148 |
| Avg chunks per doc | 2.08 |
| Embed model | `all-MiniLM-L6-v2` (384-dim) |
| Embed throughput (chunks/sec, CPU) | `_FILL_` |
| Vector footprint (math) | 148 × 384 × 4 B = **227,328 B ≈ 222 KiB** |
| `vectors.npy` on disk | `_FILL_` bytes |
| `vectors.faiss` on disk | `_FILL_` bytes |

**Retrieval quality — pure vector (baseline)**

| k | Recall@k | Notes |
|---|---|---|
| 1 | `_FILL_` | The right doc *first* |
| 3 | `_FILL_` | The typical top-k users see |
| 10 | `_FILL_` | Ceiling before reranking would kick in |
| MRR | `_FILL_` | Where in the ranking the first relevant doc appears |

**Retrieval quality — hybrid (BM25 + vector via RRF, k_rrf=60)**

| k | Recall@k | Δ vs pure vector |
|---|---|---|
| 1 | `_FILL_` | `_FILL_` |
| 3 | `_FILL_` | `_FILL_` |
| 10 | `_FILL_` | `_FILL_` |
| MRR | `_FILL_` | `_FILL_` |

**BM25-alone as a sanity baseline** (RRF is only meaningful if both parents are decent):

| k | Recall@k |
|---|---|
| 1 | `_FILL_` |
| 3 | `_FILL_` |
| 10 | `_FILL_` |
| MRR | `_FILL_` |

---

## 2. Chunking experiment — 32/8 vs 64/16

I ran one variant against the baseline: **chunk_size=64 tokens, overlap=16**. Rationale: the corpus averages 47 tokens/doc; at 32/8, most docs split into 2–3 chunks and the second chunk often trails off mid-thought. At 64/16, roughly 40% of docs collapse to a single chunk and the rest overlap generously — closer to the "no chunking" degenerate case, but not all the way there.

| Config | Chunks | Recall@1 (vec) | Recall@3 (vec) | Recall@10 (vec) | MRR (vec) | Recall@3 (hybrid) |
|---|---|---|---|---|---|---|
| 32/8 (baseline) | 148 | `_FILL_` | `_FILL_` | `_FILL_` | `_FILL_` | `_FILL_` |
| 64/16 (alt) | `_FILL_` | `_FILL_` | `_FILL_` | `_FILL_` | `_FILL_` | `_FILL_` |
| Δ | `_FILL_` | `_FILL_` | `_FILL_` | `_FILL_` | `_FILL_` | `_FILL_` |

**What I expected vs what happened.** My prior: bigger chunks should *help* on synthesis queries (`q08 exactly-once`, `q10 cut redshift costs`) where the answer is stitched across sentences, and *hurt* on narrow lookup queries (`q03 bucketing vs partitioning`) where a small focused chunk gives the embedding a cleaner signal. Fill in the actual delta after the run and note which prediction held.

**Why this matters (interview lens).** The point of running the sweep isn't to find "the right chunk size" — there isn't one. It's to prove you understand chunk size is empirical, corpus-specific, and query-mix-dependent. If the interviewer asks "what chunk size do you use?" the answer is "I measure recall@k across candidates; here's what won on my last corpus and here's why." That's the delta between senior and staff.

---

## 3. Failure analysis — one query where retrieval was wrong

Pick **one** query where recall@3 was < 1.0 and fill this in from the eval output. Candidates I'd predict struggle on this corpus:

- **`q09: kinesis vs kafka on aws for high throughput`** — this is a comparison query. If the corpus has a doc primarily about Kinesis and another primarily about Kafka, pure-vector retrieval often returns *both Kafka docs* (the query mentions Kafka twice via "kinesis vs kafka") and drops the Kinesis one. This is the classic "embedding averages the intent" failure.
- **`q11: avoid duplicate writes when a service publishes to kafka`** — the phrase "avoid duplicates" doesn't literally appear in the ground-truth doc, which talks about idempotent producers / message keys / exactly-once. BM25 will miss it entirely; vector should find it. If it doesn't, the chunker probably split the key concept across a boundary.
- **`q14: when to pick lambda architecture vs kappa in 2026`** — only 1 relevant doc. If the retriever puts it at rank 4+, that's a ranking (not recall) problem — good MRR candidate for the discussion.

**Template to fill in after the run:**

> Query: `_FILL_ (e.g., q09)`
> Ground truth doc(s): `_FILL_`
> Top-3 retrieved (pure vector): `_FILL_`
> Why it missed: `_FILL_ (2–3 sentences — vocabulary mismatch? chunk boundary? query dominated by one term?)`
> Did hybrid recover it? `_FILL_ (yes/no + which ranker contributed the recovery)`

**The staff-engineer read.** A failure analysis of one query isn't just a debugging exercise — it's the moment you tell the interviewer *how you'd fix this in production*. The three fixes worth naming: (a) query rewriting / HyDE for underspecified queries, (b) metadata-scoped retrieval so a "kinesis vs kafka" query filters to the streaming topic before ranking, (c) a cross-encoder reranker over top-20 to re-score with query-chunk attention rather than independent embeddings.

---

## 4. Cost reality check — this pipeline at 100M docs on AWS

Scaling from 71 docs to 100M is 6 orders of magnitude and every part of this pipeline changes. Here's the design I'd bring to a whiteboard.

**Assumptions.**
- Same avg doc length (~47 tokens) — call it ~64 model tokens after tokenizer inflation, so ~150M model tokens after tokenization.
- Same 2:1 chunk-to-doc ratio → **~200M chunks** to embed.
- 384-dim float32 vectors → **200M × 384 × 4 B = 307 GB** raw vectors on disk.

**Embedding compute.** On CPU, MiniLM-L6 does ~200–400 chunks/sec per core. On a modern GPU (g5.xlarge = 1× A10G) it does ~4–8k/sec with batch 128. Two feasible plans:

1. **AWS Bedrock Batch with Titan Text Embeddings v2** (1024-dim, but same math applies). Priced roughly $0.02 per 1k input tokens on-demand; Batch is ~50% cheaper. Rough back-of-envelope: 150M tokens × $0.00001/token ≈ **$1,500** for one full pass. Simple, no infra, but you inherit Titan's quality and dimension choice (larger vectors → more storage).
2. **EMR on EC2** with a Spark job that shards chunks across executors, each running MiniLM (or bge-small) locally on GPU. At ~5k chunks/sec/GPU, 200M chunks / 5k = 40k GPU-seconds = ~11 GPU-hours. On g5.xlarge spot ($0.40/hr) that's **~$5** of compute, plus driver/orchestration overhead, easily under **$50** end-to-end. Cheaper per unit, but you own the operational surface.

**Why not Glue?** Glue is great for the *chunking* step (Spark on ephemeral workers, S3-to-S3, no GPU needed). It's a poor fit for the embed step — no GPU workers, and Python UDFs on Glue lose most of their speed advantage. Realistic split: **Glue for 01_ingest_chunk (chunk + shard), EMR-on-EKS with G5 nodes for 02_embed, then either OpenSearch Serverless (managed vector) or a custom FAISS-IVF-PQ sharded index on EC2 for retrieval.**

**Vector index choice at 200M vectors.**
- `IndexFlatIP` (the lab): 307 GB in RAM, ~200M dot products per query. Dead on arrival.
- `IndexIVFFlat` (nlist ≈ 4096 clusters, nprobe ≈ 32): ~1% recall loss vs Flat, 100× faster. Still ~300 GB storage.
- `IndexIVFPQ` (product quantization to ~64 bytes/vector): **~12.8 GB** total, fits in one node's RAM, ~1–5% recall loss. This is the production sweet spot. OpenSearch's `faiss` engine and pgvector's IVFFlat both wrap the same underlying algorithm.
- **HNSW**: better recall/latency trade-off than IVF*, but memory-hungry (~1.5× vector size) and no PQ variant in mainstream libs. Good pick if you have RAM to burn.

**Total ballpark for the full re-index of 100M docs:** compute $50–$1,500 depending on plan, storage $8–$40/mo (S3 for raw vectors, EBS/mem for the served index), OpenSearch Serverless at that scale ≈ $2k–$5k/mo. The single biggest lever isn't the model — it's whether you re-embed the whole corpus on schema changes or use content-hash caching to only touch new/changed chunks.

**What I'd measure before signing off on the design.** Cost is the easy part. The hard question is: what fraction of queries need the fresh index vs a 24-hour-stale one? If 95% of the traffic is fine with daily-batch, you route those through the cheap batch-built index and keep a tiny online-updated tier for the rest. **Latency SLA + freshness SLA together determine the architecture — not vector count.**

---

## 5. One thing I'd do differently for production

**Version the chunking strategy as part of the retrieval contract**, not as script parameters.

Concretely: today, `01_ingest_chunk.py` has `CHUNK_SIZE_TOKENS = 32` as a module constant. If I change it, the next embed job silently produces vectors that live in the same FAISS index next to the old ones. Query time returns a mix of two-chunk-size worlds, and no metric will explain why recall degraded — because the metric depends on the eval set matching the index which matches the chunk config.

In production I'd:

1. Attach a `chunk_strategy_id` (e.g. `v2-fixed-64-16-mini-lm`) to every chunk in `meta.parquet`.
2. Make it a required field on the vector search query — mixed strategies are an error, not a silent bug.
3. Blue/green re-index on any strategy change: dual-write to `index_v2` behind a flag, run the eval set against both, cut over only when v2's recall@k is ≥ v1 within tolerance on the full eval set. Kill switch back to v1.
4. Log the `chunk_strategy_id` on every retrieval call so query-quality regressions in production can be tied to the exact chunker version, not "something changed last Tuesday."

This is the same discipline schema versioning brings to a warehouse. Retrievers are downstream consumers of the chunker; treat the chunker's output like a public interface.

---

## Appendix — what the interviewer will actually ask about this

Rough script to have loaded before the next round of interviews. The answers below are the 60-second versions.

**"Walk me through your chunking strategy."**
> Fixed-token, 32 whitespace tokens with 8 overlap for the lab corpus, because the docs are short and I wanted 2–3 chunks per doc to test whether the chunker was earning its keep. In production the size is corpus- and query-shape-dependent and I'd sweep 3 configs and pick by recall@k on a labeled eval set — the tutorial default of "512/50" is a code smell.

**"How do you measure whether retrieval is working?"**
> Recall@k at doc level and MRR on a labeled eval set. On this lab, 15 queries with ground-truth relevant docs. In production you grow the eval set from thumbs-down feedback and use LLM-as-judge with a stronger model to scale labeling beyond hand-annotation.

**"Why hybrid retrieval?"**
> Vector search misses exact-token cases — error codes, SKUs, proper nouns — and BM25 misses paraphrase. RRF fuses them without needing to tune weights across incompatible score scales. Anthropic's 2024 contextual retrieval paper reports ~49% reduction in retrieval failures with contextual embeddings + contextual BM25 + reranker vs embeddings alone.

**"Would you scale this to 100M docs?"**
> Same pipeline, different physics. Glue for chunking, GPU nodes for embedding, IVF-PQ for the served index, and the biggest architectural question is freshness SLA — is a 24-hour-stale index acceptable, and if so you route 95% of traffic through the cheap batch tier.

**"What's the top thing you'd change?"**
> Version the chunking strategy as a first-class field in the vector store. Silent chunker changes are the #1 source of "retrieval got worse and nobody knows why" incidents.
