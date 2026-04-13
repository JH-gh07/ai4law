from datetime import datetime

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str


class ReportArtifact(BaseModel):
    id: str
    owner_type: str
    owner_id: str
    artifact_type: str
    file_path: str
    preview: dict = Field(default_factory=dict)
    created_at: datetime
