"""
06_capture_metrics.py — One-shot metrics capture for the Lab 01 writeup.

Runs the full pipeline twice (baseline + an alternative chunking config),
captures stdout from each step, records index-size-on-disk and elapsed times,
and writes everything to learning-notes/lab-01-run-log.txt.

You run this once. You paste the numbers from the log into the writeup.

Rationale (Staff-engineer lens):
  Reproducibility matters. If your writeup quotes numbers, another engineer
  should be able to re-run one command and verify them. This script is the
  contract between "I ran the lab" and "here are my results."

Run:
    python src/06_capture_metrics.py
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB_ROOT = HERE.parent
REPO_ROOT = LAB_ROOT.parent.parent  # <repo>/learning-notes lives up two
LOG_DIR = REPO_ROOT / "learning-notes"
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / "lab-01-run-log.txt"

INGEST_SCRIPT = HERE / "01_ingest_chunk.py"
EMBED_SCRIPT = HERE / "02_embed_index.py"
EVAL_SCRIPT = HERE / "04_evaluate.py"
HYBRID_SCRIPT = HERE / "05_hybrid.py"

DATA_DIR = LAB_ROOT / "data"
INDEX_PATH = DATA_DIR / "vectors.faiss"
VECTORS_PATH = DATA_DIR / "vectors.npy"
CHUNKS_PATH = DATA_DIR / "chunks.jsonl"

# Configs we sweep. (size, overlap, label)
CONFIGS = [
    (32, 8,  "baseline"),
    (64, 16, "medium-chunks"),  # the alternative for the "chunking experiment" deliverable
]


def run(cmd: list[str]) -> tuple[str, float]:
    """Run a subprocess, capture stdout, return (output, elapsed_seconds)."""
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    dt = time.time() - t0
    out = proc.stdout + ("\n[STDERR]\n" + proc.stderr if proc.stderr else "")
    if proc.returncode != 0:
        out += f"\n[non-zero exit: {proc.returncode}]"
    return out, dt


def patch_ingest_config(size: int, overlap: int) -> None:
    """Rewrite CHUNK_SIZE_TOKENS / CHUNK_OVERLAP_TOKENS in 01_ingest_chunk.py."""
    src = INGEST_SCRIPT.read_text()
    src = re.sub(r"^CHUNK_SIZE_TOKENS\s*=\s*\d+",
                 f"CHUNK_SIZE_TOKENS = {size}", src, count=1, flags=re.M)
    src = re.sub(r"^CHUNK_OVERLAP_TOKENS\s*=\s*\d+",
                 f"CHUNK_OVERLAP_TOKENS = {overlap}", src, count=1, flags=re.M)
    INGEST_SCRIPT.write_text(src)


def index_bytes_on_disk() -> tuple[int, int]:
    """(faiss_bytes, npy_bytes). Both may be 0 if the file doesn't exist."""
    fb = INDEX_PATH.stat().st_size if INDEX_PATH.exists() else 0
    nb = VECTORS_PATH.stat().st_size if VECTORS_PATH.exists() else 0
    return fb, nb


def n_chunks_written() -> int:
    if not CHUNKS_PATH.exists():
        return 0
    with CHUNKS_PATH.open() as f:
        return sum(1 for line in f if line.strip())


def format_section(title: str, body: str) -> str:
    bar = "=" * 78
    return f"\n{bar}\n{title}\n{bar}\n{body}\n"


def main() -> None:
    py = sys.executable
    log_buf = io.StringIO()

    with redirect_stdout(log_buf):
        print(f"lab-01 metrics capture — {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"python: {py}")
        print(f"lab_root: {LAB_ROOT}")

        # Snapshot the original config so we restore it at the end.
        original_ingest = INGEST_SCRIPT.read_text()

        try:
            for size, overlap, label in CONFIGS:
                print(format_section(
                    f"CONFIG: {label}  (chunk_size={size}, overlap={overlap})",
                    ""
                ))

                patch_ingest_config(size, overlap)

                # 1. Chunk
                out, dt = run([py, str(INGEST_SCRIPT)])
                print(format_section(f"[{label}] 01_ingest_chunk.py  ({dt:.2f}s)", out))

                # 2. Embed + index
                out, dt = run([py, str(EMBED_SCRIPT)])
                print(format_section(f"[{label}] 02_embed_index.py  ({dt:.2f}s)", out))

                fb, nb = index_bytes_on_disk()
                nc = n_chunks_written()
                print(f"[{label}] chunks_written={nc}  "
                      f"vectors.faiss={fb} bytes ({fb/1024:.1f} KiB)  "
                      f"vectors.npy={nb} bytes ({nb/1024:.1f} KiB)")

                # 3. Evaluate pure-vector
                out, dt = run([py, str(EVAL_SCRIPT)])
                print(format_section(f"[{label}] 04_evaluate.py  ({dt:.2f}s)", out))

                # 4. Evaluate hybrid
                out, dt = run([py, str(HYBRID_SCRIPT)])
                print(format_section(f"[{label}] 05_hybrid.py  ({dt:.2f}s)", out))

        finally:
            # Restore the original ingest script so `git diff` after this run
            # is empty (except for artifacts under data/).
            INGEST_SCRIPT.write_text(original_ingest)
            print("\nRestored original 01_ingest_chunk.py config.")

    LOG_PATH.write_text(log_buf.getvalue())
    print(f"Wrote {LOG_PATH}")
    print("\nNext: open learning-notes/lab-01-writeup.md and fill in the marked slots")
    print("using the numbers from the log.")


if __name__ == "__main__":
    main()
