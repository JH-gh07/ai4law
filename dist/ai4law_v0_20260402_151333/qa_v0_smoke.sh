#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p outputs/qa
LOG_FILE="outputs/qa/v0_smoke_$(date +%Y%m%d_%H%M%S).log"

{
  echo "[qa] start v0 smoke at $(date '+%Y-%m-%d %H:%M:%S')"
  .venv311/bin/pytest -q \
    backend/modules/v0_task_gateway/tests/test_api.py \
    backend/modules/assessment/tests/test_async_api.py \
    backend/modules/pipia/tests/test_async_api.py \
    backend/modules/bcr/tests/test_async_api.py \
    backend/modules/dpia/tests/test_async_api.py \
    backend/modules/tia/tests/test_async_api.py \
    backend/modules/cn_flow/tests/test_async_api.py \
    backend/modules/cpra/tests/test_async_api.py
  echo "[qa] done at $(date '+%Y-%m-%d %H:%M:%S')"
} | tee "$LOG_FILE"

echo "[qa] log saved: $LOG_FILE"

