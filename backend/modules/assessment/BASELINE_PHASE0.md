# Assessment Phase 0 Baseline

## Current Call Chain

1. `AssessmentService.generate_report()` records the request trace.
2. `ProfileExtractor.extract()` copies request fields into `CompanyProfile` and stores per-file text previews in `extracted_notes`.
3. `DiagnosisService.evaluate()` computes `recommended_path`; non-`security_assessment` paths are blocked unless `force_override_path=true`.
4. `AssessmentRetriever.search()` builds the RAG query from industry, purpose, receiver country, CIIO status, and important-data status.
5. `AssessmentChapterGenerator.generate()` computes `risk_level`, builds a context block from profile and regulations, then generates eight fixed chapters.
6. `ConsistencyChecker.check()` verifies chapter citations and the final chapter risk label for mandatory high-risk conditions.
7. `check_cn_alignment()` scans generated chapter text for obvious CIIO, important-data, industry, and receiver-country conflicts.
8. `AssessmentReportRenderer.render()` writes Markdown, DOCX, and ZIP outputs.
9. `TraceRecorder.write_manifest()` writes the trace manifest and `AssessmentResult` returns generated paths.

## Phase 0 Scope

- Preserve current business behavior.
- Add regression coverage for the current assessment flow.
- Do not introduce workflow schemas, facts, issues, evidence, or context packs yet.
- Do not change prompt construction or report content logic yet.

## Known Baseline Limitations

- Attachment previews are not included in the assessment chapter prompt.
- The trace manifest lists trace event files; detailed payloads live in per-event JSON files.
- There is no assessment `IssueItem`, `EvidenceItem`, or unified `GenerationContextPack` yet.
- Current consistency checks are limited and do not validate facts/issues/evidence.
