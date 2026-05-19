from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from backend.common.workflow import GenerationContextPack
from backend.common.workflow.trace import dump_model_list


@dataclass
class WorkflowRunResult:
    diagnosis: Any
    profile: Any
    regulations: list[Any]
    chapters: list[Any]
    consistency_issues: list[str]
    outputs: dict[str, str]
    facts: list[Any]
    issues: list[Any]
    evidence_chain: list[Any]
    context_pack: GenerationContextPack


class WorkflowPipeline:
    def __init__(
        self,
        *,
        extract_profile: Callable[[Any], Any],
        evaluate_diagnosis: Callable[[Any], Any],
        validate_path: Callable[[Any, str, str], str | None],
        build_facts: Callable[[Any, Any, Any], list[Any]],
        retrieve_regulations: Callable[[Any], list[Any]],
        build_attachment_notes: Callable[[Any], list[dict[str, str]]],
        build_issues: Callable[[list[Any], Any, list[Any], list[dict[str, str]]], list[Any]],
        build_evidence: Callable[[list[Any], list[Any], list[Any], Any], tuple[list[Any], list[Any]]],
        build_context_pack: Callable[..., GenerationContextPack],
        generate_chapters: Callable[[Any, list[Any], GenerationContextPack], list[Any]],
        check_consistency: Callable[[Any, list[Any], GenerationContextPack], list[str]],
        check_alignment: Callable[[str, Any], list[str]],
        render_artifacts: Callable[..., dict[str, str]],
        request_event_name: str = "assessment_request",
        consistency_check_labels: list[str] | None = None,
    ) -> None:
        self.extract_profile = extract_profile
        self.evaluate_diagnosis = evaluate_diagnosis
        self.validate_path = validate_path
        self.build_facts = build_facts
        self.retrieve_regulations = retrieve_regulations
        self.build_attachment_notes = build_attachment_notes
        self.build_issues = build_issues
        self.build_evidence = build_evidence
        self.build_context_pack = build_context_pack
        self.generate_chapters = generate_chapters
        self.check_consistency = check_consistency
        self.check_alignment = check_alignment
        self.render_artifacts = render_artifacts
        self.request_event_name = request_event_name
        self.consistency_check_labels = consistency_check_labels or [
            "legacy_chapter",
            "context_pack_references",
            "report_against_context",
        ]

    def run(self, *, payload: Any, task_id: str, trace: Any) -> WorkflowRunResult:
        trace.record(self.request_event_name, payload.model_dump())

        profile = self.extract_profile(payload)
        trace.record("profile_extracted", profile.model_dump())

        diagnosis = self.evaluate_diagnosis(payload)
        diagnosis_payload = diagnosis.model_dump() if hasattr(diagnosis, "model_dump") else {"value": diagnosis}
        trace.record("diagnosis", diagnosis_payload)

        path_warning = self.validate_path(payload, diagnosis.recommended_path, diagnosis.rationale)
        trace.record("path_validation", {"warning": path_warning, "recommended_path": diagnosis.recommended_path})

        facts = self.build_facts(payload, profile, diagnosis)
        trace.record("facts_built", {"facts": dump_model_list(facts)})

        regulations = self.retrieve_regulations(profile)
        trace.record("retrieval_hits", {"hit_count": len(regulations), "hits": dump_model_list(regulations)})

        attachment_notes = self.build_attachment_notes(profile)
        issues = self.build_issues(facts, diagnosis, regulations, attachment_notes)
        trace.record("issues_built", {"issues": dump_model_list(issues)})

        issues, evidence_chain = self.build_evidence(facts, issues, regulations, diagnosis)
        trace.record(
            "evidence_built",
            {
                "issues": dump_model_list(issues),
                "evidence_chain": dump_model_list(evidence_chain),
            },
        )

        context_pack = self.build_context_pack(
            task_id=task_id,
            diagnosis=diagnosis,
            facts=facts,
            regulations=regulations,
            issues=issues,
            evidence_chain=evidence_chain,
            path_warning=path_warning,
            attachment_notes=attachment_notes,
        )
        trace.record("context_pack_built", context_pack.model_dump())

        chapters = self.generate_chapters(profile, regulations, context_pack)
        trace.record("chapters_generated", {"chapter_count": len(chapters)})

        consistency_issues = self.check_consistency(profile, chapters, context_pack)
        trace.record(
            "consistency_issues",
            {
                "issues": list(consistency_issues),
                "checks": list(self.consistency_check_labels),
            },
        )

        report_content = "\n".join(chapter.content for chapter in chapters)
        alignment_issues = self.check_alignment(report_content, profile)
        trace.record("alignment_issues", {"issues": list(alignment_issues)})

        if alignment_issues:
            consistency_issues.extend(alignment_issues)
        if path_warning:
            consistency_issues.append(path_warning)

        manifest = trace.write_manifest()
        alignment_warning = "；".join(alignment_issues) if alignment_issues else None
        outputs = self.render_artifacts(
            task_id=task_id,
            payload=payload,
            profile=profile,
            regulations=regulations,
            chapters=chapters,
            path_warning=path_warning,
            alignment_warning=alignment_warning,
            issues=issues,
            evidence_chain=evidence_chain,
            attachment_notes=attachment_notes,
            trace_manifest_path=str(manifest),
            facts=facts,
            diagnosis=diagnosis,
        )

        return WorkflowRunResult(
            diagnosis=diagnosis,
            profile=profile,
            regulations=regulations,
            chapters=chapters,
            consistency_issues=consistency_issues,
            outputs=outputs,
            facts=facts,
            issues=issues,
            evidence_chain=evidence_chain,
            context_pack=context_pack,
        )
