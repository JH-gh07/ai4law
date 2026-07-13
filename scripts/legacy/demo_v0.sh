#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[demo] Start API server:"
echo "  .venv311/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000"
echo
echo "[demo] Health check:"
echo "  curl http://127.0.0.1:8000/health"
echo
echo "[demo] Unified task gateway sample (module 4.2):"
cat <<'EOF'
curl -X POST 'http://127.0.0.1:8000/api/v0/tasks' \
  -H 'Content-Type: application/json' \
  -d '{
    "module_code": "4.2",
    "session_id": "demo-session",
    "input_payload": {
      "company_name": "DemoCo",
      "business_model": "SaaS",
      "data_lifecycle": "collect-process-store-delete",
      "notice_and_consent": "notice exists",
      "consumer_rights_process": "SLA 45 days",
      "opt_out_and_sale_sharing": "no sale/share",
      "vendor_management": "DPA baseline",
      "attachments": [{
        "file_role": "privacy_policy",
        "file_name": "policy.url",
        "file_format": "url",
        "storage_uri": "https://example.com/privacy"
      }]
    },
    "attachment_ids": []
  }'
EOF
echo
echo "[demo] then poll:"
echo "  curl http://127.0.0.1:8000/api/v0/tasks/<task_id>"
echo "  curl http://127.0.0.1:8000/api/v0/tasks/<task_id>/artifacts"
echo "  curl http://127.0.0.1:8000/api/v0/tasks/<task_id>/audit"

