# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal learning portfolio tracking a Senior → Staff Data Engineer transition. It contains a roadmap (`00_ROADMAP.md`, `01_WEEK_1.md`), hands-on labs under `labs/`, and write-ups under `learning-notes/`. Each lab is a self-contained project with its own `README.md`, `requirements.txt`, and `.venv/`.

The stack anchor is AWS (Redshift/EMR/Glue/S3), but labs run **locally by default** to avoid cloud costs. Architectural notes in each lab README call out how the local design maps to production AWS.

## Working directory conventions

- **Per-lab virtualenvs.** There is no repo-root venv. Every lab has its own `.venv/` created inside the lab directory. Always `cd` into the lab before running Python.
- **Source data is committed, derived data is not.** `corpus.jsonl` and `eval_queries.jsonl` are checked in; `chunks.jsonl`, `vectors.npy`, `vectors.faiss`, `meta.parquet` are regenerable and gitignored (see `.gitignore` for exact rules).
- **`scripts/`** is gitignored entirely — it contains local machine-setup scripts that may embed corporate identifiers. Don't add repo-level tooling there; put it elsewhere.
- **`.env`** is gitignored; `.env.example` is the shape reference. LLM API keys go in `.env` when future labs need them.

## Common commands

Setup for any lab (replace `<lab-folder>`):

```bash
cd labs/<lab-folder>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Lab 01 (`labs/01-embeddings-semantic-search/`)

The pipeline is a sequence of numbered scripts run **as scripts, not imports** (filenames start with digits, so they aren't valid module names — each script uses `Path(__file__).resolve().parent` to locate `data/`, and stages communicate only via files on disk):

```bash
python src/01_ingest_chunk.py    # corpus.jsonl → chunks.jsonl (fixed-token chunker with overlap)
python src/02_embed_index.py     # chunks.jsonl → vectors.npy + vectors.faiss + meta.parquet
python src/03_search.py          # interactive CLI (or: python src/03_search.py "query" --k 5)
python src/04_evaluate.py        # recall@1/3/10 + MRR against eval_queries.jsonl (pure vector)
python src/05_hybrid.py          # BM25 + vector fused with Reciprocal Rank Fusion; evals all three
python src/06_capture_metrics.py # runs 01→02→04→05 across chunking configs, logs to learning-notes/lab-01-run-log.txt
```

First run of `02_embed_index.py` downloads a ~90 MB sentence-transformers model to `~/.cache/torch/sentence_transformers/`.

There is no test suite, linter config, or Makefile in this repo yet. `06_capture_metrics.py` serves as the reproducibility harness: it patches `CHUNK_SIZE_TOKENS`/`CHUNK_OVERLAP_TOKENS` in `01_ingest_chunk.py`, re-runs the pipeline for each config, and **restores the original file** in its `finally` block. If you edit that script, preserve the restore or `git diff` after a metrics run will be dirty.

## Architecture: how the Lab 01 pipeline fits together

The retrieval pipeline is deliberately staged so re-indexing doesn't require re-embedding (embedding is the expensive step). The invariant that ties the stages together is **positional alignment**: the row index in `meta.parquet` equals the FAISS `vec_id` equals the BM25 corpus position. Break that ordering and every downstream lookup silently corrupts.

```
corpus.jsonl ──▶ 01_ingest_chunk ──▶ chunks.jsonl
                                        │
                                        ▼
                               02_embed_index
                                (SentenceTransformer, batch, L2-normalize)
                                        │
                          ┌─────────────┼─────────────┐
                          ▼             ▼             ▼
                    vectors.npy    vectors.faiss  meta.parquet
                    (raw floats)   (IndexFlatIP)  (vec_id → chunk metadata)
                          │             │             │
                          └────┬────────┴─────────────┘
                               ▼
              03_search / 04_evaluate / 05_hybrid
              (all rebuild the model + read the index; 05 also builds BM25 from meta['text'])
```

Key design choices that matter when editing:

- **L2-normalized vectors + `IndexFlatIP`** means inner product equals cosine similarity. If you change to a different index type (IVF, HNSW), keep the normalization or scores will not be cosines anymore.
- **Doc-level recall, not chunk-level.** `04_evaluate.py` retrieves `k*4` chunks then de-dupes to unique `doc_id`s before scoring — a query is "served" if any chunk from a relevant doc appears in top-k. When adding metrics, keep this doc-level semantic or the numbers become incomparable.
- **Off-topic queries** (empty `relevant_doc_ids`) are excluded from the aggregate via `dropna` — they exist to test failure behavior (score threshold), not to score.
- **RRF in `05_hybrid.py`** uses `k_rrf=60` and fuses `RETRIEVE_N=30` candidates per ranker. It's parameter-light on purpose (no per-corpus tuning between BM25 and cosine score scales). Two rankers can be extended to three (e.g., a cross-encoder re-ranker) by appending another ranking to `rrf_fuse`'s input list.
- **Content-hash chunk IDs** (`sha256[:16]` of the chunk text in `01_ingest_chunk.py`) exist so a caching/idempotence layer can key on them. That layer is a documented stretch challenge (Stretch A), not yet implemented — treat re-runs as full rebuilds today.

## Style expectations

The lab scripts favor extended module docstrings that frame the *why* (interview lens, staff-engineer perspective, trade-off notes) and end with a commented-out "STRETCH" block listing follow-up experiments. Match that style when adding scripts in this repo — this is a learning portfolio, so context/reasoning in comments is a feature, not clutter.
