#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p outputs/qa
LOG_FILE="outputs/qa/frontend_linkage_$(date +%Y%m%d_%H%M%S).log"

{
  echo "[frontend] start linkage check at $(date '+%Y-%m-%d %H:%M:%S')"
  PYTHONPATH="$ROOT_DIR" .venv311/bin/python scripts/frontend_v0_linkage_check.py
  echo "[frontend] done at $(date '+%Y-%m-%d %H:%M:%S')"
} | tee "$LOG_FILE"

echo "[frontend] log saved: $LOG_FILE"

