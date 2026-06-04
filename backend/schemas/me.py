from datetime import datetime

from pydantic import BaseModel, Field


class MyTaskItem(BaseModel):
    id: str
    source: str
    status: str
    created_at: datetime
    updated_at: datetime
    module: str | None = None


class MyTasksResponse(BaseModel):
    items: list[MyTaskItem] = Field(default_factory=list)


class MyReportItem(BaseModel):
    id: str
    owner_type: str
    owner_id: str
    artifact_type: str
    file_path: str
    created_at: datetime
    preview: dict = Field(default_factory=dict)


class MyReportsResponse(BaseModel):
    items: list[MyReportItem] = Field(default_factory=list)


class RecoveredModuleRun(BaseModel):
    id: str
    task_space_id: str
    module: str
    run_mode: str = "async"
    started_at: datetime
    finished_at: datetime | None = None
    success: bool = False
    request: dict = Field(default_factory=dict)
    response: dict | None = None
    error: str | None = None
    async_task_id: str | None = None
    async_state: str | None = None


class RecoveredWorkspaceItem(BaseModel):
    task_id: str
    module: str
    status: str
    created_at: datetime
    updated_at: datetime
    run: RecoveredModuleRun | None = None
    artifacts: list[MyReportItem] = Field(default_factory=list)


class RecoveredWorkspaceResponse(BaseModel):
    items: list[RecoveredWorkspaceItem] = Field(default_factory=list)


class ReportMetadataResponse(BaseModel):
    owner_id: str
    version: str
    risk_level: str | None = None
    summary: str | None = None
