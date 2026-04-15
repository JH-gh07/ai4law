from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.common.rag.ingest import build_regulation_index


def main() -> None:
    settings = SimpleNamespace(
        rag_source_jsonl=ROOT / "doc/knowledge/normalized/regulation_articles.jsonl",
        rag_index_path=ROOT / "storage/rag/regulation_index_v2.json",
        rag_embedding_dimension=384,
    )
    index_path = build_regulation_index(settings)
    print(f"RAG vector index built at: {index_path}")


if __name__ == "__main__":
    main()
