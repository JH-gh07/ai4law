from __future__ import annotations

import argparse
import json

from backend.common.rag.eval import run_all_evals, run_generation_eval, run_retrieval_eval


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CN + Review layered RAG evaluation.")
    parser.add_argument(
        "--mode",
        choices=["retrieval", "generation", "all"],
        default="all",
        help="Which evaluation suite to run.",
    )
    args = parser.parse_args()

    if args.mode == "retrieval":
        result = run_retrieval_eval()
    elif args.mode == "generation":
        result = run_generation_eval()
    else:
        result = run_all_evals()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
