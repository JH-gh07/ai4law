from __future__ import annotations

from pathlib import Path

from backend.common.workflow import FactItem, GenerationContextPack, IssueItem
from backend.common.workflow.pipeline import WorkflowPipeline


class _DummyTrace:
    def __init__(self, tmp_path: Path) -> None:
        self.events: list[str] = []
        self._tmp_path = tmp_path

    def record(self, name: str, payload: dict) -> None:
        self.events.append(name)

    def write_manifest(self) -> Path:
        manifest = self._tmp_path / "manifest.json"
        manifest.write_text("{}", encoding="utf-8")
        return manifest


class _Payload:
    def __init__(self) -> None:
        self.company_name = "测试公司"
        self.force_override_path = False

    def model_dump(self) -> dict:
        return {"company_name": self.company_name}


class _Model:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)

    def model_dump(self) -> dict:
        return dict(self.__dict__)


class _DumpModel:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def model_dump(self) -> dict:
        return dict(self._payload)


def test_pipeline_runs_all_steps_and_outputs_artifacts(tmp_path: Path) -> None:
    facts = [FactItem(fact_id="FACT-1", source_type="schema", value="x", field_path="request.company_name")]
    issues = [
        IssueItem(
            issue_id="ISSUE-1",
            title="路径问题",
            description="描述",
            category="path",
            severity="HIGH",
            fact_refs=["FACT-1"],
            recommended_action="修复",
        )
    ]
    evidence_chain = [_DumpModel({"evidence_id": "EVIDENCE-1"})]
    diagnosis = _Model(recommended_path="security_assessment", rationale="ok", risk_level="HIGH")
    profile = _Model(industry="医疗", is_ciio=True, contains_important_data=False, receiver_country="SG")
    regulations = [_DumpModel({"source_id": "reg-1"})]
    chapters = [_Model(content="ISSUE-1 已处理")]
    trace = _DummyTrace(tmp_path)

    pipeline = WorkflowPipeline(
        extract_profile=lambda payload: profile,
        evaluate_diagnosis=lambda payload: diagnosis,
        validate_path=lambda payload, path, rationale: None,
        build_facts=lambda payload, p, d: facts,
        retrieve_regulations=lambda p: regulations,
        build_attachment_notes=lambda p: [],
        build_issues=lambda f, d, r, a: issues,
        build_evidence=lambda f, i, r, d: (i, evidence_chain),
        build_context_pack=lambda **kwargs: GenerationContextPack(
            module_key="assessment",
            request_id=kwargs["task_id"],
            facts=kwargs["facts"],
            diagnosis_result=kwargs["diagnosis"].model_dump(),
            regulations=[item.model_dump() for item in kwargs["regulations"]],
            issues=kwargs["issues"],
            evidence_chain=[],
        ),
        generate_chapters=lambda p, r, c: chapters,
        check_consistency=lambda p, ch, c: [],
        check_alignment=lambda content, p: [],
        render_artifacts=lambda **kwargs: {"docx": "x.docx"},
    )

    result = pipeline.run(payload=_Payload(), task_id="task-1", trace=trace)

    assert result.facts
    assert result.issues
    assert result.outputs["docx"] == "x.docx"
    assert trace.events == [
        "assessment_request",
        "profile_extracted",
        "diagnosis",
        "path_validation",
        "facts_built",
        "retrieval_hits",
        "issues_built",
        "evidence_built",
        "context_pack_built",
        "chapters_generated",
        "consistency_issues",
        "alignment_issues",
    ]
