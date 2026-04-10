from pydantic import BaseModel, Field


class KnowledgeSummary(BaseModel):
    source_count: int
    case_count: int
    p0_source_count: int


class KnowledgeSourceOptions(BaseModel):
    layers: list[str] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)


class KnowledgeCaseOptions(BaseModel):
    modules: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)


class KnowledgeIndexResponse(BaseModel):
    summary: KnowledgeSummary
    source_options: KnowledgeSourceOptions
    case_options: KnowledgeCaseOptions
    sources: list[dict[str, str]] = Field(default_factory=list)
    cases: list[dict[str, str]] = Field(default_factory=list)


class KnowledgeSourceDetailResponse(BaseModel):
    item: dict[str, str]
    preview: str = ""


class KnowledgeCaseDetailResponse(BaseModel):
    item: dict[str, str]
    preview: str = ""


class KnowledgeCitationResponse(BaseModel):
    query: str
    matched: dict[str, str] | None = None
    preview: str = ""
