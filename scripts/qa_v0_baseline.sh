#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p outputs/qa
LOG_FILE="outputs/qa/v0_baseline_$(date +%Y%m%d_%H%M%S).log"

{
  echo "[baseline] start at $(date '+%Y-%m-%d %H:%M:%S')"
  PYTHONPATH="$ROOT_DIR" .venv311/bin/python scripts/qa_v0_baseline.py "$@"
  echo "[baseline] done at $(date '+%Y-%m-%d %H:%M:%S')"
} | tee "$LOG_FILE"

echo "[baseline] log saved: $LOG_FILE"
