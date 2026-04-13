#!/usr/bin/env python3
"""Archive current rag v2 evaluation outputs as dated regression snapshots."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SRC_JSON = ROOT / "qa/rag_eval_v2.json"
SRC_MD = ROOT / "doc/v2/qa-rag-v2.md"
OUT_DIR = ROOT / "qa/regression"


def main() -> None:
    if not SRC_JSON.exists() or not SRC_MD.exists():
        raise FileNotFoundError("Please run `python3 scripts/qa_rag_eval_v2.py` first.")

    stamp = datetime.now().strftime("%Y%m%d")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_json = OUT_DIR / f"rag_eval_v2_{stamp}.json"
    out_md = OUT_DIR / f"rag_eval_v2_{stamp}.md"

    shutil.copy2(SRC_JSON, out_json)
    shutil.copy2(SRC_MD, out_md)

    print(f"snapshot json: {out_json}")
    print(f"snapshot md: {out_md}")


if __name__ == "__main__":
    main()
