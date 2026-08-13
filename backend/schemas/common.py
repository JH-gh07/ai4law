from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field



class ReportArtifact(BaseModel):
    id: str
    owner_type: str
    owner_id: str
    artifact_type: str
    file_path: str
    preview: dict = Field(default_factory=dict)
    created_at: datetime


class ArtifactPreviewResponse(BaseModel):
    path: str
    file_name: str
    kind: str
    render_mode: str
    content: str = ""
    file_url: str | None = None
    # Structured report body. Only populated when a *registered*
    # ``artifact_type=document_ir_json`` record passes DocumentIR validation.
    # When set, ``content`` stays empty: structured content must never be
    # mixed into the raw-text ``content`` field (task067 T04).
    report_ir: dict[str, Any] | None = None
