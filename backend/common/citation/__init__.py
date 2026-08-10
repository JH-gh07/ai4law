from backend.common.citation.compiler import (
    ClaimBindingReport,
    CompiledFootnotes,
    compile_footnote_map,
    extract_citation_markers,
    extract_citation_marker_count,
    markers_in_text_equal_footnote_map,
    simulate_marker_addition,
    simulate_marker_removal,
    validate_all_markers,
    validate_citation_marker,
    validate_claim_bindings,
)
from backend.common.citation.id_generator import generate_citation_id, LAW_ABBREVIATIONS
from backend.common.citation.models import AuthorityLevel, BindingForce, CitationItem, CitationType
from backend.common.citation.registry import CitationRegistry

__all__ = [
    "AuthorityLevel",
    "BindingForce",
    "CitationItem",
    "CitationRegistry",
    "CitationType",
    "ClaimBindingReport",
    "CompiledFootnotes",
    "compile_footnote_map",
    "extract_citation_markers",
    "extract_citation_marker_count",
    "generate_citation_id",
    "LAW_ABBREVIATIONS",
    "markers_in_text_equal_footnote_map",
    "simulate_marker_addition",
    "simulate_marker_removal",
    "validate_all_markers",
    "validate_citation_marker",
    "validate_claim_bindings",
]
