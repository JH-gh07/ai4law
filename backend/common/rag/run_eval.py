from __future__ import annotations

import argparse
import json

from backend.common.rag.eval import run_all_evals, run_generation_eval, run_retrieval_eval


def main() -> int:
    parser = argparse.ArgumentParser(description="Run layered RAG evaluation.")
    parser.add_argument(
        "--mode",
        choices=["retrieval", "generation", "all"],
        default="all",
        help="Which evaluation suite to run.",
    )
    parser.add_argument(
        "--target",
        choices=["cn", "eu", "us", "all"],
        default="cn",
        help="Which jurisdiction bundle to run.",
    )
    args = parser.parse_args()

    if args.mode == "retrieval":
        result = run_retrieval_eval(target=args.target)
    elif args.mode == "generation":
        result = run_generation_eval(target=args.target)
    else:
        result = run_all_evals(target=args.target)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
