# Lab 01 — Semantic Search over a DE Corpus (Embeddings, FAISS, Eval)

**Prerequisite:** `week_01_embeddings_lab.py` (the toy 20-sentence version). This lab
levels it up to something that mirrors a real RAG-retrieval pipeline you'd ship at a
product company.

**Time budget:** 2.5 – 3.5 hours.
**Stack:** Python 3.10+, `sentence-transformers` (local, no API keys), `faiss-cpu`, `rank-bm25`, `numpy`, `pandas`.

---

## Why this lab

The toy version taught you the mental model:

> An embedding maps text → high-dim vector where semantic neighbors are close in cosine space.

That's the *concept*. But every senior DE interview and every real RAG project bottlenecks
on **retrieval quality**, not on the model. So this lab is deliberately unbalanced toward
the parts most tutorials skip:

1. Chunking (the highest-leverage decision in a RAG pipeline).
2. Metadata design in the vector store (this is a data-modeling problem, not an ML one).
3. Retrieval **evaluation** with recall@k on labeled queries.
4. Hybrid search (BM25 + vector) — because pure vector search underperforms in most real corpora and you should know why.

Every one of these shows up in Staff-level interview questions and in production incident
postmortems. Master this lab and you're already ahead of most DEs who've dabbled in RAG.

---

## What you'll build

```
                 ┌───────────────────────┐
                 │ corpus.jsonl (71 docs)│
                 └───────────┬───────────┘
                             │  01_ingest_chunk.py
                             ▼
                 ┌───────────────────────┐
                 │ chunks.jsonl          │  (doc_id, chunk_id, text, metadata)
                 └───────────┬───────────┘
                             │  02_embed_index.py
                             ▼
                 ┌───────────────────────┐
                 │ FAISS index + meta.pq │  (vectors on disk, metadata sidecar)
                 └───────────┬───────────┘
                             │  03_search.py         (interactive CLI)
                             │  04_evaluate.py       (recall@k, MRR)
                             │  05_hybrid.py         (BM25 + vector fusion)
                             ▼
                       You: an engineer who
                       can defend every design
                       choice in an interview
```

---

## The corpus

`data/corpus.jsonl` — 71 short paragraphs on 8 DE topics:
Spark internals, Delta/Iceberg, Kafka/streaming, warehouse cost, CDC, orchestration,
data quality, and system design patterns. Each document has a `doc_id` and a `topic` tag.
Average doc length is ~47 whitespace-tokens; range is 36–63.

`data/eval_queries.jsonl` — 15 queries. Each carries a list of `relevant_doc_ids` — the ground
truth for scoring retrieval. Some queries are single-topic ("what causes Spark shuffle skew?");
some span topics ("how do lakehouses simplify streaming ingestion?"); one is deliberately
off-topic to test how your system fails.

---

## Step-by-step

### 0. Install

```bash
cd labs/01-embeddings-semantic-search
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

First run downloads a ~90 MB model to `~/.cache/torch/sentence_transformers/`.

### 1. Chunk (`src/01_ingest_chunk.py`)

Reads `corpus.jsonl`, applies a **fixed-token chunker with overlap**, writes `chunks.jsonl`.

Run it, then open `chunks.jsonl` and answer to yourself:

- How many chunks did 71 docs produce? Why that number?
- What happens at chunk boundaries — is any sentence split in half?
- If a doc is shorter than `chunk_size`, does it become one chunk or zero?

Heads up: with the defaults (`chunk_size=32`, `overlap=8`), most docs will split
into 2–3 chunks. Try `chunk_size=200` and you'll see every doc collapse into a
single chunk — that's the "no chunking" degenerate case. Feel the difference.

**Interview lens:** "Walk me through your chunking strategy" is a top-5 RAG interview
question in 2026. The answer isn't "512 tokens with 50 overlap." It's *why* you picked
those numbers for *this* content and how you'd measure whether they're right. Try the
alternatives at the bottom of the script.

### 2. Embed + index (`src/02_embed_index.py`)

Loads chunks, batches them into the model, normalizes embeddings, writes a **FAISS
IndexFlatIP** (inner product = cosine on L2-normalized vectors) plus a sidecar
`meta.parquet` mapping `vec_id → chunk metadata`.

Watch the console output for two numbers:

- **Embed throughput** (chunks/sec) — this is the DE knob. On CPU, MiniLM-L6 hits ~100–400 chunks/sec depending on your machine.
- **Index size on disk** — `n_vectors * dim * 4 bytes`. Prove the math.

**Staff-engineer perspective:** In production this pipeline is idempotent and
resumable. The script demonstrates the pattern with content-hash IDs — re-run it
twice, and the second run should be a no-op (or should be, once you complete the
stretch challenge).

### 3. Search (`src/03_search.py`)

Interactive CLI. Type a query, get top-k chunks + scores. Try:

- `what causes shuffle skew?`
- `how do we cut redshift costs?`
- `explain data mesh`
- `what time is dinner`   ← the deliberate failure case

For each: look at scores, not just ranks. A top-1 with cosine 0.72 is very different
from a top-1 with cosine 0.28. This intuition — *the score, not the rank* — is what
separates production RAG from demo RAG.

### 4. Evaluate (`src/04_evaluate.py`)

Runs all 15 eval queries, computes **recall@1, recall@3, recall@10**, and **MRR**.
This is the part 95% of tutorials skip.

Report the numbers. If recall@3 is above ~0.75 you've built something respectable.
If it's below ~0.5, either the corpus is harder than expected or your chunking is
hurting you — check which and fix it.

**Interview lens:** "How would you measure whether your RAG retrieval is working?"
Answer with recall@k, MRR, and — critically — the fact that you need **labeled
data** to compute either. Bonus points if you mention LLM-as-judge for scaling
label creation beyond what humans can annotate.

### 5. Hybrid (`src/05_hybrid.py`)

Adds BM25 (classic keyword scoring) and combines it with the vector score using
**Reciprocal Rank Fusion**. Re-runs the eval.

Almost always, hybrid > pure vector on a heterogeneous corpus. Report the delta.
If hybrid didn't help you, that itself is a finding — dig in.

**Staff-engineer perspective:** Pure vector search fails on rare tokens (product
codes, error codes, IDs), and BM25 fails on paraphrase. Real search systems use
both. Elastic/OpenSearch calls this hybrid retrieval; you now know how it works
under the hood.

---

## Deliverable

Create `learning-notes/lab-01-writeup.md` in your portfolio repo with:

1. **Numbers:** embed throughput, chunk count, index size on disk, recall@1/3/10 for pure vector, recall@1/3/10 for hybrid.
2. **Chunking experiment:** try one alternative (bigger chunks OR different overlap OR sentence-aware chunking) and report whether it helped.
3. **Failure analysis:** pick one query where retrieval was wrong and explain why in 2–3 sentences.
4. **Cost reality check:** if this corpus were 100M docs on AWS, what would the embedding job look like? (Batch size, Glue vs. EMR vs. Bedrock Batch, cost estimate.)
5. **One thing you'd do differently** if you were designing this for production.

That doc becomes an interview talking point.

---

## Stretch challenges

Any two of these convert this lab into a portfolio piece.

- **A. Content-hash caching:** modify `02_embed_index.py` to skip chunks whose hash
  is already in the index. Prove idempotence: run twice, second run does zero embed
  calls.
- **B. Model comparison:** swap the model to `BAAI/bge-small-en-v1.5` (same
  dimensionality, generally higher quality). Re-run eval. Which won?
- **C. Metadata filtering:** add a topic filter to `03_search.py` so users can scope
  to one topic. In FAISS this means either an `IndexIDMap` + post-filter or building
  per-topic sub-indexes. Discuss the trade-off in your writeup.
- **D. Sentence-aware chunker:** replace the fixed-token chunker with one that
  respects sentence boundaries (NLTK/spaCy). Does recall@3 improve?

---

## What "done" looks like

- All five scripts run cleanly.
- You can articulate — in a single paragraph — why hybrid retrieval typically beats pure vector.
- You know your recall@k numbers by heart for the next 24 hours.
- The writeup exists in your portfolio.

When you're done, ping me — we'll debrief the numbers, and then I'm pulling
System Design forward for the next thread.
