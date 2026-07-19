from datetime import datetime

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
