#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
schema_file="$(mktemp "${TMPDIR:-/tmp}/ai4law-openapi.XXXXXX")"

cleanup() {
  rm -f "${schema_file}"
}
trap cleanup EXIT

cd "${repo_root}"
uv run --frozen python -m scripts.export_openapi --output "${schema_file}"
npm exec --prefix frontend -- openapi-typescript "${schema_file}" \
  --default-non-nullable false \
  --output frontend/src/api/generated/openapi.d.ts
