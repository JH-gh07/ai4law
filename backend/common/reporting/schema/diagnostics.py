"""Compiler diagnostics shared by all validation passes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

DiagnosticSeverity = Literal["info", "warning", "error", "fatal"]


class DiagnosticLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str | None = None
    block_id: str | None = None
    field: str | None = None
    citation_id: str | None = None


class Diagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: DiagnosticSeverity
    message: str
    location: DiagnosticLocation | None = None
    suggestion: str | None = None
