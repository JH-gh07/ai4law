#!/usr/bin/env python3
"""Archive current RAG retrieval benchmark outputs as dated regression snapshots."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SRC_JSON = ROOT / "outputs/benchmarks/rag_retrieval.json"
SRC_MD = ROOT / "outputs/benchmarks/rag_retrieval.md"
OUT_DIR = ROOT / "outputs/benchmarks/regression"


def main() -> None:
    if not SRC_JSON.exists() or not SRC_MD.exists():
        raise FileNotFoundError("Please run `python scripts/run_rag_retrieval_benchmark.py` first.")

    stamp = datetime.now().strftime("%Y%m%d")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_json = OUT_DIR / f"rag_retrieval_{stamp}.json"
    out_md = OUT_DIR / f"rag_retrieval_{stamp}.md"

    shutil.copy2(SRC_JSON, out_json)
    shutil.copy2(SRC_MD, out_md)

    print(f"snapshot json: {out_json}")
    print(f"snapshot md: {out_md}")


if __name__ == "__main__":
    main()
