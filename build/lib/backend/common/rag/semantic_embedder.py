from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class SemanticEmbedder:
    """基于 sentence-transformers 的语义 Embedding，支持中英双语。

    默认模型: moka-ai/m3e-base（768维，MIT协议，本地离线运行）
    """

    def __init__(self, model_name: str = "moka-ai/m3e-base", device: str = "cpu") -> None:
        from sentence_transformers import SentenceTransformer

        # 显式使用 CPU 避免 MPS 显存溢出（苹果 Silicon 统一内存限制）
        self.model = SentenceTransformer(model_name, device=device)
        self.dimension: int = self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> list[float]:
        """对单条文本编码，返回 L2 归一化的稠密向量。"""
        return self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 64,
        show_progress: bool = True,
    ) -> list[list[float]]:
        """批量编码，用于建索引。"""
        return self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=show_progress,
        ).tolist()

    @staticmethod
    def similarity(v1: list[float], v2: list[float]) -> float:
        """余弦相似度（向量已归一化时等同于点积）。"""
        return float(sum(a * b for a, b in zip(v1, v2)))
