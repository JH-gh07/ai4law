# BCR Layout Regression Fixtures (task067)

This directory holds the *frozen, reproducible* failure signals used to prove
that the pre-fix BCR renderer violates the layout contract, and that the new
IR renderer fixes it. It intentionally contains **no user-sensitive document
body text** — only structure signatures, metrics, and tiny synthetic
stress snippets.

## What belongs here

- `frozen_failure_modes.json` — machine-readable fingerprints of the six
  column-grid failure modes observed on the pre-fix baseline (task
  `4ab0776d9ddc49faba4d7bf89f30cd0a`).
- Synthetic stress fixtures for the renderer tests (T08): long English words,
  mixed CJK/Latin titles, three-level clause numbering, cross-page findings.
- Golden v4 IR fixtures once T01/T02 freeze the contract (NOT yet present).

## What must NOT be committed here

- Real company names, clauses, or extracted BCR document bodies.
- Any content from `backend/tests/fixtures/eu/bcr_c_globaltech.docx` beyond its
  existing role as the approved test input.

The approved sample input for T10 visual acceptance is
`backend/tests/fixtures/eu/bcr_c_globaltech.docx` (an existing, already
approved test asset) — not a copy of production uploads.
