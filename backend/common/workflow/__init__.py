"""L1 Platform workflow models.

These are the platform's shared data types — every module consumes and produces
objects from this namespace.  No module should define its own Fact, Issue,
Evidence, or Action model; they should use (and optionally extend) these.

Architecture layers:
    facts      →  what we know and how we know it
    issues     →  what's wrong and how certain we are
    evidence   →  which laws / documents support each conclusion
    action     →  what to do about it (remediation, materials, roadmap)
    expression →  what language is safe for external reports
    trace      →  auditable record of every decision
"""

from backend.common.workflow.action import (
    ActionPlan,
    MaterialItem,
    RemediationAction,
    StagePlan,
)
from backend.common.workflow.context_pack import GenerationContextPack
from backend.common.workflow.evidence import (
    CitationBinding,
    DocumentRef,
    EvidenceItem,
    EvidencePack,
    build_citation_bindings,
    regulation_to_citation,
)
from backend.common.workflow.expression import (
    ExpressionStrategy,
    ForbiddenExpressionRule,
    cn_forbidden_expressions,
)
from backend.common.workflow.facts import (
    EvidenceStatus,
    FactMergeCandidate,
    FactMergeLog,
    FactPack,
    FactItem,
    FactSourceType,
)
from backend.common.workflow.input_manifest import (
    ParserStatus,
    RunInputEntry,
    RunInputEntryPublic,
    RunInputIntegrity,
    RunInputManifest,
    RunInputManifestPublic,
    SourceKind,
    compute_manifest_hash,
    public_entry,
    public_manifest,
    seal_manifest,
    verify_manifest_hash,
)
from backend.common.workflow.issues import (
    IssueCategory,
    IssueCertainty,
    IssueItem,
    IssueSeverity,
)
from backend.common.workflow.missing import (
    MissingItem,
    MissingManifest,
    MissingRootCause,
    MissingStatus,
    MissingType,
    validate_missing_item,
    validate_missing_manifest,
    validate_missing_source_paths,
)
from backend.common.workflow.pipeline import WorkflowPipeline
from backend.common.workflow.trace import (
    TraceEvent,
    TraceManifest,
    TraceStep,
)

__all__ = [
    # facts
    "EvidenceStatus",
    "FactItem",
    "FactMergeCandidate",
    "FactMergeLog",
    "FactPack",
    "FactSourceType",
    # issues
    "IssueCategory",
    "IssueCertainty",
    "IssueItem",
    "IssueSeverity",
    # missing (task081)
    "MissingItem",
    "MissingManifest",
    "MissingRootCause",
    "MissingStatus",
    "MissingType",
    "validate_missing_item",
    "validate_missing_manifest",
    "validate_missing_source_paths",
    # input manifest (task068 run-input traceability)
    "ParserStatus",
    "RunInputEntry",
    "RunInputEntryPublic",
    "RunInputIntegrity",
    "RunInputManifest",
    "RunInputManifestPublic",
    "SourceKind",
    "compute_manifest_hash",
    "public_entry",
    "public_manifest",
    "seal_manifest",
    "verify_manifest_hash",
    # evidence
    "CitationBinding",
    "DocumentRef",
    "EvidenceItem",
    "EvidencePack",
    "build_citation_bindings",
    "regulation_to_citation",
    # action
    "ActionPlan",
    "MaterialItem",
    "RemediationAction",
    "StagePlan",
    # expression
    "ExpressionStrategy",
    "ForbiddenExpressionRule",
    "cn_forbidden_expressions",
    # trace
    "TraceEvent",
    "TraceManifest",
    "TraceStep",
    # context
    "GenerationContextPack",
    # pipeline
    "WorkflowPipeline",
]
