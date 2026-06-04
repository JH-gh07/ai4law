from pydantic import BaseModel, Field


class KnowledgeSummary(BaseModel):
    source_count: int
    case_count: int


class KnowledgeSourceOptions(BaseModel):
    categories: list[str] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)
    usages: list[str] = Field(default_factory=list)


class KnowledgeCaseOptions(BaseModel):
    jurisdictions: list[str] = Field(default_factory=list)
    scenarios: list[str] = Field(default_factory=list)


class KnowledgeSyncMeta(BaseModel):
    synced_at: str
    cache_refreshed: bool = False
    sources_csv_path: str
    cases_csv_path: str
    module_catalog_path: str = ""
    spec_asset_manifest_path: str = ""
    sources_csv_exists: bool
    cases_csv_exists: bool
    module_catalog_exists: bool = False
    spec_asset_manifest_exists: bool = False
    sources_csv_mtime: str = ""
    cases_csv_mtime: str = ""
    module_catalog_mtime: str = ""
    spec_asset_manifest_mtime: str = ""
    manifest_total_files: int = 0
    manifest_frontend_visible_files: int = 0
    manifest_migrated_files: int = 0


class KnowledgeIndexResponse(BaseModel):
    summary: KnowledgeSummary
    sync_meta: KnowledgeSyncMeta
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


class KnowledgeSearchItem(BaseModel):
    id: str
    title: str
    article: str
    content: str
    jurisdiction: str = ""
    path: str = ""
    doc_type: str = ""
    source_url: str = ""
    keywords: list[str] = Field(default_factory=list)


class KnowledgeSearchResponse(BaseModel):
    query: str
    jurisdiction: str | None = None
    path: str | None = None
    mode: str = "hybrid"
    top_k: int = 8
    hit_count: int
    items: list[KnowledgeSearchItem] = Field(default_factory=list)


class ArticleDetailResponse(BaseModel):
    source_id: str
    title: str
    article_no: str
    article_content: str = ""
    prev_article_no: str | None = None
    prev_article_content: str = ""
    next_article_no: str | None = None
    next_article_content: str = ""
    source_url: str = ""
    authority_level: str = "medium"
    binding_force: str = "recommended"
    jurisdiction: str = "cn"
    doc_type: str = "law"
