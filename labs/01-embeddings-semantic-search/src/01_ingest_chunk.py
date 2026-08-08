"""
01_ingest_chunk.py — Ingest the corpus and produce chunks.

Why chunking matters (Staff-engineer lens):
  Chunk size is the single biggest lever in a RAG pipeline. Too large, and each
  chunk contains multiple ideas — the embedding vector averages them together
  and semantic search degrades. Too small, and each chunk lacks context — the
  embedding lacks discriminative signal, and downstream generation lacks material
  to answer with. The right answer is empirical: chunk, embed, eval, adjust.

This script uses a fixed-token chunker with overlap. The chunker treats
whitespace-separated tokens as the unit. That is a *simplification*: real
production chunkers count model tokens (via tiktoken or the model's own
tokenizer) because that is the boundary that actually matters for the model.
Sentence-aware chunking is the stretch challenge.

Run:
    python src/01_ingest_chunk.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterator

HERE = Path(__file__).resolve().parent
LAB_ROOT = HERE.parent
CORPUS_PATH = LAB_ROOT / "data" / "corpus.jsonl"
CHUNKS_PATH = LAB_ROOT / "data" / "chunks.jsonl"

# Chunker config — tune these and watch the eval numbers change.
# NOTE: this corpus is tight (avg 47 words/doc, max 63). Picking 32/8 forces
# most docs to split into 2–3 chunks so you actually see the chunker at work.
# For long-form corpora (articles, docs, transcripts) 200–400 tokens is more
# typical.
CHUNK_SIZE_TOKENS = 128
CHUNK_OVERLAP_TOKENS = 0


def chunk_text(text: str, size: int, overlap: int) -> Iterator[str]:
    """Fixed-token chunker with overlap.

    Trade-off note: this splits on whitespace which is *not* how the model
    tokenizes. For MiniLM the ratio is roughly 1 whitespace-token to 1.3 model
    tokens, so 80 whitespace-tokens ≈ 100 model tokens. Good enough for a lab;
    in production count real tokens.
    """
    tokens = text.split()
    if not tokens:
        return
    if len(tokens) <= size:
        yield " ".join(tokens)
        return
    step = size - overlap
    if step <= 0:
        raise ValueError("overlap must be smaller than size")
    for start in range(0, len(tokens), step):
        window = tokens[start : start + size]
        if not window:
            break
        yield " ".join(window)
        if start + size >= len(tokens):
            break


def content_hash(text: str) -> str:
    """Stable ID for a chunk. Two chunks with identical text share an ID —
    that is exactly what you want for caching and idempotent re-embeds."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main() -> None:
    if not CORPUS_PATH.exists():
        raise SystemExit(f"corpus not found at {CORPUS_PATH}")

    n_docs = 0
    n_chunks = 0
    with CORPUS_PATH.open() as fin, CHUNKS_PATH.open("w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            n_docs += 1
            for chunk_idx, chunk in enumerate(
                chunk_text(doc["text"], CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_TOKENS)
            ):
                record = {
                    "chunk_id": content_hash(chunk),
                    "doc_id": doc["doc_id"],
                    "chunk_index": chunk_idx,
                    "topic": doc.get("topic", "unknown"),
                    "text": chunk,
                    "n_tokens_ws": len(chunk.split()),
                }
                fout.write(json.dumps(record) + "\n")
                n_chunks += 1

    print(f"Docs ingested: {n_docs}")
    print(f"Chunks written: {n_chunks} → {CHUNKS_PATH.name}")
    print(f"Avg chunks per doc: {n_chunks / max(n_docs, 1):.2f}")
    print(
        f"Config: chunk_size={CHUNK_SIZE_TOKENS} tokens, overlap={CHUNK_OVERLAP_TOKENS} tokens"
    )


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# STRETCH: try these values and re-run 02/04. Record the eval numbers.
#
#   CHUNK_SIZE_TOKENS = 16,   CHUNK_OVERLAP_TOKENS = 4    (very small)
#   CHUNK_SIZE_TOKENS = 64,   CHUNK_OVERLAP_TOKENS = 16   (medium)
#   CHUNK_SIZE_TOKENS = 200,  CHUNK_OVERLAP_TOKENS = 0    (no chunking — every doc = 1 chunk)
#   CHUNK_SIZE_TOKENS = 32,   CHUNK_OVERLAP_TOKENS = 0    (no overlap)
#
# Prediction to test: smaller chunks help recall@k on narrow queries but hurt
# recall on queries that need integration across sentences. Which held for
# your corpus?
# ---------------------------------------------------------------------------
