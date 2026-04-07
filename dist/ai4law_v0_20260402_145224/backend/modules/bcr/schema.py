from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


BCRCode = Literal[
    "3.2-C1",
    "3.2-C2",
    "3.2-C3",
    "3.2-C4",
    "3.2-C5",
    "3.2-C6",
    "3.2-C7",
    "3.2-C8",
    "3.2-C9",
    "3.2-C10",
]
BCRScore = Literal["compliant", "partial", "non_compliant"]


class BCRReviewItem(BaseModel):
    code: BCRCode
    title: str = Field(min_length=2)
    score: BCRScore
    finding: str = Field(min_length=2)
    legal_basis: str = Field(min_length=2)
    recommendation: str = Field(min_length=2)
    evidence: str = Field(default="")


class BCRAttachment(BaseModel):
    file_name: str = Field(min_length=1)
    file_format: Literal["pdf", "docx"]
    storage_uri: str = Field(min_length=1)


class BCRRequest(BaseModel):
    company_name: str = Field(min_length=2)
    review_items: list[BCRReviewItem] = Field(min_length=1)
    attachments: list[BCRAttachment] = Field(default_factory=list)
    uploaded_files: list[str] = Field(default_factory=list)


class BCRProblem(BaseModel):
    code: BCRCode
    title: str
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    finding: str
    legal_basis: str
    recommendation: str
    evidence: str = ""


class BCRChapter(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    risk_level: str


class BCRResult(BaseModel):
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    company_name: str
    rating: Literal["基本合规", "部分缺失", "高风险"]
    problems: list[BCRProblem] = Field(default_factory=list)
    chapters: list[BCRChapter] = Field(default_factory=list)
    consistency_issues: list[str] = Field(default_factory=list)
    attachment_notes: list[str] = Field(default_factory=list)


class BCRAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class BCRAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: BCRResult | None = None

