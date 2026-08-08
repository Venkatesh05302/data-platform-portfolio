# Data Platform Portfolio

A working portfolio of production-shaped Data Engineering and AI/LLM engineering work — built alongside a 6-12 month plan to move from Senior Data Engineer into a Staff/Lead role at a top product company.

Everything here is code I've actually run, with results captured. No tutorials copied from Medium, no "hello world" projects.

## What's in this repo

| Path | What it is |
|------|-----------|
| [`00_ROADMAP.md`](./00_ROADMAP.md) | The 6-12 month plan — tracks (System Design, AI/LLM, Spark, SQL), weekly time allocation, and the reasoning behind the sequencing. |
| [`01_WEEK_1.md`](./01_WEEK_1.md) | Week 1 self-assessment, baseline ratings, and initial focus. |
| [`labs/`](./labs/) | Hands-on labs. Each is a self-contained project with its own README, `requirements.txt`, and results. |
| [`system-designs/`](./system-designs/) | Written system-design case studies. Framework + 5 canonical DE designs. |
| [`learning-notes/`](./learning-notes/) | Notes, diagrams, and write-ups from concepts I've studied. |

## Labs

### [Lab 01 — Embeddings & Semantic Search](./labs/01-embeddings-semantic-search/)

End-to-end retrieval pipeline: chunking → local embeddings (MiniLM-L6-v2) → FAISS index → search CLI → labeled evaluation (recall@k, MRR) → **hybrid retrieval** with BM25 + Reciprocal Rank Fusion.

Deliberately front-loads what most RAG tutorials skip: retrieval evaluation with labeled queries, hybrid retrieval, and chunking as an empirical decision.

**Status:** Complete. Metrics captured in the lab's README.

## About the stack anchor

Production experience is on **AWS** — Redshift, EMR, Glue, S3. Labs here run **locally by default** (no cloud costs) but architectural notes call out how each piece maps to a production AWS deployment.

## Local setup (any lab)

```bash
cd labs/<lab-folder>
python -m venv .venv
source .venv/bin/activate         # macOS/Linux
pip install -r requirements.txt
```

Each lab's README documents its own entry points.

## Notes on structure

- **Source data** (`corpus.jsonl`, `eval_queries.jsonl`) is committed. **Derived data** (embeddings, indexes, chunks) is regenerable and ignored via `.gitignore`.
- Virtual environments (`.venv/`) are per-machine and never committed.
- Secrets go in `.env` (also ignored). Any `.env.example` files show the shape without real values.
