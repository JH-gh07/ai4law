#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

bash scripts/qa_v0_smoke.sh

mkdir -p dist
STAMP="$(date +%Y%m%d_%H%M%S)"
REL_DIR="dist/ai4law_v0_${STAMP}"
mkdir -p "$REL_DIR"

cp -R backend "$REL_DIR/"
cp pyproject.toml "$REL_DIR/"
cp README.md "$REL_DIR/"
cp doc/v2/plan.md "$REL_DIR/"
cp scripts/demo_v0.sh "$REL_DIR/"
cp scripts/qa_v0_smoke.sh "$REL_DIR/"

{
  echo "release_time: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "git_commit: $(git rev-parse --short HEAD)"
  echo "python: $(.venv311/bin/python --version 2>&1)"
} > "$REL_DIR/release_manifest.txt"

tar -czf "${REL_DIR}.tar.gz" -C dist "$(basename "$REL_DIR")"
echo "[release] package generated: ${REL_DIR}.tar.gz"

