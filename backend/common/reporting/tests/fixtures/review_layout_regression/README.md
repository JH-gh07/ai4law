# review_layout_regression (task068 T00)

Public, desensitized regression fixture for the `review` document-special-review
layout pipeline. It exercises the two defects that the fix must close:

1. **I068-02** — `AggregatedReview.issues` flattened into `list[str]` (findings lost).
2. **I068-22** — one finding bound to multiple citations, rendered as `；`.join(labels)
   with no per-citation rationale.

This is *approved test material* only (synthetic clause titles / GDPR labels), never
real user content. The fixture is referenced by the T00 `baseline_manifest.json` and
later consumed by T02/T10 regression tests.

Files:
- `review_findings_input.json` — desensitized structured findings (3 issues, one
  multi-citation) used to seed `AggregatedReview` in regression tests.
