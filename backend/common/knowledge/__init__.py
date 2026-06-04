from __future__ import annotations

from importlib import import_module

__all__ = [
    "ChineseLegalChunker",
    "DocumentParser",
    "IngestStatus",
    "IngestedFile",
    "KnowledgeChunk",
    "KnowledgeDocument",
    "KnowledgeStorageManager",
    "LegalChunk",
    "ParsedDocument",
]

_EXPORT_MAP = {
    "ChineseLegalChunker": "backend.common.knowledge.chunker",
    "LegalChunk": "backend.common.knowledge.chunker",
    "DocumentParser": "backend.common.knowledge.document_parser",
    "ParsedDocument": "backend.common.knowledge.document_parser",
    "IngestedFile": "backend.common.knowledge.models",
    "KnowledgeChunk": "backend.common.knowledge.models",
    "KnowledgeDocument": "backend.common.knowledge.models",
    "IngestStatus": "backend.common.knowledge.models",
    "KnowledgeStorageManager": "backend.common.knowledge.storage_manager",
}


def __getattr__(name: str):
    module_name = _EXPORT_MAP.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value
