"""Fail-closed compiler gates for the new reporting IR.

This is an additive Stage A slice. It validates IR before any legacy renderer
is used; it does not replace the current report generation path yet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.common.reporting.schema import DocumentIR
from backend.common.reporting.schema.citations import CitationRegistry
from backend.common.reporting.schema.diagnostics import Diagnostic, DiagnosticLocation

_RESIDUAL_MARKER_RE = re.compile(r"\{\{(?:CIT-[^}]+|[^}]+)\}\}")
_BOLD_RE = re.compile(r"\*\*|(?<!\w)__")
_FOOTNOTE_RE = re.compile(r"(?<!\w)\[(\d+)\]")


@dataclass
class CompilerState:
    document: DocumentIR
    registry: CitationRegistry
    rendered_text: str = ""
    diagnostics: list[Diagnostic] = field(default_factory=list)


@dataclass(frozen=True)
class PassResult:
    status: str = "success"
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class CompileResult:
    status: str
    document: DocumentIR | None
    diagnostics: tuple[Diagnostic, ...]


class CompilerPass:
    def run(self, state: CompilerState) -> PassResult:
        raise NotImplementedError


def _result(diagnostics: list[Diagnostic]) -> PassResult:
    if any(item.severity == "fatal" for item in diagnostics):
        status = "fatal"
    elif any(item.severity == "error" for item in diagnostics):
        status = "error"
    elif any(item.severity == "warning" for item in diagnostics):
        status = "warning"
    else:
        status = "success"
    return PassResult(status=status, diagnostics=tuple(diagnostics))


class InputValidationPass(CompilerPass):
    def run(self, state: CompilerState) -> PassResult:
        diagnostics: list[Diagnostic] = []
        seen_sections: set[str] = set()
        seen_blocks: set[str] = set()
        for section in state.document.sections:
            if section.section_id in seen_sections:
                diagnostics.append(Diagnostic(
                    code="SECTION_ID_DUPLICATE",
                    severity="fatal",
                    message=f"重复的 section_id: {section.section_id}",
                    location=DiagnosticLocation(section_id=section.section_id),
                ))
            seen_sections.add(section.section_id)
            for block in section.blocks:
                if block.block_id in seen_blocks:
                    diagnostics.append(Diagnostic(
                        code="BLOCK_ID_DUPLICATE",
                        severity="error",
                        message=f"重复的 block_id: {block.block_id}",
                        location=DiagnosticLocation(section_id=section.section_id, block_id=block.block_id),
                    ))
                seen_blocks.add(block.block_id)
        return _result(diagnostics)


class CitationValidationPass(CompilerPass):
    def run(self, state: CompilerState) -> PassResult:
        diagnostics: list[Diagnostic] = []
        for section in state.document.sections:
            for block in section.blocks:
                citation_refs = getattr(block, "citation_refs", [])
                for citation_id in citation_refs:
                    if state.registry.resolve(citation_id) is None:
                        diagnostics.append(Diagnostic(
                            code="CITATION_NOT_REGISTERED",
                            severity="error",
                            message=f"引用 ID 未注册: {citation_id}",
                            location=DiagnosticLocation(
                                section_id=section.section_id,
                                block_id=block.block_id,
                                citation_id=citation_id,
                            ),
                            suggestion="将 citation_id 注册到本次 DocumentIR 的 CitationRegistry",
                        ))
        return _result(diagnostics)


class CitationNumberingPass(CompilerPass):
    def run(self, state: CompilerState) -> PassResult:
        for section in state.document.sections:
            for block in section.blocks:
                for citation_id in getattr(block, "citation_refs", []):
                    state.registry.assign_footnote_number(citation_id)
        return PassResult()


class DedupValidationPass(CompilerPass):
    def run(self, state: CompilerState) -> PassResult:
        diagnostics: list[Diagnostic] = []
        seen: dict[str, tuple[str, str]] = {}
        for section in state.document.sections:
            if section.reuse_policy != "single_use":
                continue
            for block in section.blocks:
                text = getattr(block, "text", "")
                normalized = "".join(text.split()).casefold()
                if not normalized:
                    continue
                previous = seen.get(normalized)
                if previous:
                    diagnostics.append(Diagnostic(
                        code="BLOCK_DUPLICATE_SINGLE_USE",
                        severity="error",
                        message=f"single_use 内容重复: {previous[0]} 与 {section.section_id}",
                        location=DiagnosticLocation(section_id=section.section_id, block_id=block.block_id),
                    ))
                else:
                    seen[normalized] = (section.section_id, block.block_id)
        return _result(diagnostics)


class StructureValidationPass(CompilerPass):
    def run(self, state: CompilerState) -> PassResult:
        diagnostics: list[Diagnostic] = []
        previous_level = 0
        for section in state.document.sections:
            if previous_level and section.level > previous_level + 1:
                diagnostics.append(Diagnostic(
                    code="SECTION_LEVEL_SKIP",
                    severity="error",
                    message=f"章节层级跳跃: H{previous_level} -> H{section.level}",
                    location=DiagnosticLocation(section_id=section.section_id),
                ))
            previous_level = section.level
        return _result(diagnostics)


class RenderValidationPass(CompilerPass):
    def run(self, state: CompilerState) -> PassResult:
        if not state.rendered_text:
            return PassResult()
        diagnostics: list[Diagnostic] = []
        for pattern, code, message in (
            (_RESIDUAL_MARKER_RE, "RENDER_MARKER_RESIDUE", "渲染产物包含未替换模板/引用标记"),
            (_BOLD_RE, "RENDER_MARKDOWN_SYNTAX", "语义渲染产物包含未允许的粗体 Markdown 标记"),
        ):
            match = pattern.search(state.rendered_text)
            if match:
                diagnostics.append(Diagnostic(
                    code=code,
                    severity="fatal" if code == "RENDER_MARKER_RESIDUE" else "error",
                    message=message,
                ))
        return _result(diagnostics)


class DocumentCompiler:
    """Run the Stage A passes in deterministic order."""

    def __init__(self, passes: list[CompilerPass] | None = None) -> None:
        self.passes = passes or [
            InputValidationPass(),
            CitationValidationPass(),
            CitationNumberingPass(),
            DedupValidationPass(),
            StructureValidationPass(),
            RenderValidationPass(),
        ]

    def compile(
        self,
        document: DocumentIR,
        registry: CitationRegistry,
        *,
        rendered_text: str = "",
    ) -> CompileResult:
        state = CompilerState(document=document, registry=registry, rendered_text=rendered_text)
        for compiler_pass in self.passes:
            result = compiler_pass.run(state)
            state.diagnostics.extend(result.diagnostics)
            if result.status == "fatal":
                break
        state.document.diagnostics = state.diagnostics
        status = "fatal" if any(d.severity == "fatal" for d in state.diagnostics) else (
            "error" if any(d.severity == "error" for d in state.diagnostics) else "success"
        )
        return CompileResult(status=status, document=state.document, diagnostics=tuple(state.diagnostics))
