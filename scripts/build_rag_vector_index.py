"""重建 RAG 向量索引。

用法:
  python scripts/build_rag_vector_index.py            # 默认 hashing 模式
  python scripts/build_rag_vector_index.py --semantic # 语义 moka-ai/m3e-base 模式
"""
from pathlib import Path
import sys
import argparse
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.common.rag.ingest import build_regulation_index, build_semantic_regulation_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build RAG vector index")
    parser.add_argument(
        "--semantic",
        action="store_true",
        help="Use moka-ai/m3e-base semantic embedding (default: hashing)",
    )
    parser.add_argument(
        "--model",
        default="moka-ai/m3e-base",
        help="Semantic model name (only used with --semantic)",
    )
    args = parser.parse_args()

    settings = SimpleNamespace(
        rag_source_jsonl=ROOT / "doc/knowledge/normalized/regulation_articles.jsonl",
        rag_index_path=ROOT / "storage/rag/regulation_index_v2.json",
        rag_embedding_dimension=384,
        rag_semantic_index_path=ROOT / "storage/rag/regulation_index_v3.json",
        rag_semantic_model=args.model,
    )

    if args.semantic:
        print(f"使用语义 Embedding 模式：{args.model}")
        index_path = build_semantic_regulation_index(settings)
    else:
        print("使用 Hashing Embedding 模式")
        index_path = build_regulation_index(settings)

    print(f"索引已构建: {index_path}")


if __name__ == "__main__":
    main()
