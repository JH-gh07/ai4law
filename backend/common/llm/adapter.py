from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    confidence: float


class LLMAdapter:
    """Deterministic v0 adapter.

    In v0 this adapter creates stable template text so we can verify end-to-end behavior.
    """

    def summarize(self, title: str, bullet_points: list[str]) -> LLMResponse:
        lines = [f"{idx}. {point}" for idx, point in enumerate(bullet_points, start=1)]
        text = f"{title}\n" + "\n".join(lines)
        return LLMResponse(text=text, confidence=0.85)
