from enum import Enum

from pydantic import BaseModel, Field


class YesNoUnknown(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class DiagnosisAnswers(BaseModel):
    q1_is_ciio: YesNoUnknown = Field(description="Whether enterprise is CIIO")
    q2_has_important_data: YesNoUnknown = Field(description="Whether important data is exported")
    q3_pii_count: int = Field(ge=0, description="Count of personal information subjects")
    q4_spi_count: int = Field(ge=0, description="Count of sensitive personal information subjects")
    q5_purpose: str = Field(min_length=2, description="Purpose of data export")


class DiagnosisResult(BaseModel):
    recommended_path: str
    legal_basis: list[str]
    rationale: str
    action_items: list[str]
    risk_level: str


class DiagnosisReportRequest(BaseModel):
    company_name: str = Field(min_length=2)
    answers: DiagnosisAnswers


class DiagnosisReportResponse(BaseModel):
    report_path: str
    result: DiagnosisResult
