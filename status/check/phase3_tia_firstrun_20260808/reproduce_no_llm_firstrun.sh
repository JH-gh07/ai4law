#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
CASE_FILE="$REPO_ROOT/backend/tests/tia/cases/01_minimal.json"
RUN_ROOT=${TIA_EVIDENCE_RUN_ROOT:-$(mktemp -d /tmp/ai4law-tia-firstrun.XXXXXX)}
GIT_COMMIT=$(git -C "$REPO_ROOT" rev-parse HEAD)

for MODE in old new
do
  if [ "$MODE" = new ]
  then
    FLAG=true
  else
    FLAG=false
  fi

  mkdir -p "$RUN_ROOT/$MODE"
  (
    cd "$RUN_ROOT/$MODE"
    AI4LAW_SCHEMA_FIRST_TIA_ENABLED="$FLAG" \
    AI4LAW_LLM_PROVIDER=none \
    LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    PYTHONPATH="$REPO_ROOT" \
      python -B - "$CASE_FILE" "$MODE" "$GIT_COMMIT" <<'PY'
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from backend.common.runtime.run_manifest import summarize_trace
from backend.common.trace.recorder import TraceRecorder
from backend.domains.eu.tia.schema import TIARequest
from backend.domains.eu.tia.service import TIAService


class DisabledLLM:
    enabled = False
    _enabled = False


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


case_path = Path(sys.argv[1]).resolve()
mode = sys.argv[2]
commit = sys.argv[3]
task_id = "phase3-tia-no-llm"
case = json.loads(case_path.read_text(encoding="utf-8"))
payload = TIARequest.model_validate(case["input"])
trace = TraceRecorder(Path("trace"), task_id=task_id)

started_at = datetime.now(timezone.utc)
started = time.perf_counter()
result = TIAService(llm_client=DisabledLLM()).generate_report(
    payload,
    task_id=task_id,
    trace=trace,
)
duration_ms = round((time.perf_counter() - started) * 1000)
finished_at = datetime.now(timezone.utc)
trace.write_manifest()

outputs = {key: Path(value).resolve() for key, value in result.output_files.items()}
citation_map = json.loads(outputs["citation_map_json"].read_text(encoding="utf-8"))
document_ir = None
if "document_ir_json" in outputs:
    document_ir = json.loads(outputs["document_ir_json"].read_text(encoding="utf-8"))

with ZipFile(outputs["zip"]) as bundle:
    zip_members = [
        {
            "name": info.filename,
            "size": info.file_size,
            "sha256": hashlib.sha256(bundle.read(info.filename)).hexdigest(),
        }
        for info in bundle.infolist()
    ]

evidence = {
    "schema_version": "1.0",
    "mode": mode,
    "schema_first_enabled": mode == "new",
    "compiler_gate": "success" if mode == "new" else "not_enabled",
    "execution": {
        "service": "backend.domains.eu.tia.service.TIAService.generate_report",
        "task_id": task_id,
        "llm_mode": "disabled",
        "network_llm_calls": 0,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_ms": duration_ms,
        "git_commit": commit,
    },
    "fixture": {
        "path": "backend/tests/tia/cases/01_minimal.json",
        "sha256": sha256(case_path),
        "case_id": case.get("case_id"),
        "description": case.get("description"),
        "attachment_uri": payload.attachments[0].storage_uri,
        "attachment_is_real_file": False,
        "attachment_note": (
            "The storage:// URI is a fictional fixture placeholder; "
            "no attachment-content validation is claimed."
        ),
    },
    "result": {
        "risk_level": result.risk_level,
        "transfer_tool": result.transfer_tool,
        "chapter_count": len(result.chapters),
        "consistency_issues": result.consistency_issues,
        "attachment_notes": result.attachment_notes,
        "output_roles": sorted(result.output_files),
    },
    "artifacts": {
        role: {
            "path": path.name,
            "size": path.stat().st_size,
            "sha256": sha256(path),
        }
        for role, path in outputs.items()
    },
    "zip_members": zip_members,
    "citation_map": {
        "footnote_count": len(citation_map.get("footnote_map", {})),
        "all_items_count": len(citation_map.get("all_items", [])),
        "citation_ids": [
            item.get("citation_id") for item in citation_map.get("all_items", [])
        ],
    },
    "document_ir": (
        {
            "present": True,
            "schema_version": document_ir.get("schema_version"),
            "section_count": len(document_ir.get("sections", [])),
            "block_count": sum(
                len(section.get("blocks", []))
                for section in document_ir.get("sections", [])
            ),
            "claim_block_count": sum(
                block.get("type") == "claim"
                for section in document_ir.get("sections", [])
                for block in section.get("blocks", [])
            ),
            "diagnostics": document_ir.get("diagnostics", []),
        }
        if document_ir is not None
        else {"present": False}
    ),
    "observability": summarize_trace(trace),
}
evidence["observability"]["trace_manifest"] = "trace/manifest.json"
Path("run_evidence.json").write_text(
    json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(evidence, ensure_ascii=False, indent=2))
PY
  )
done

printf 'No-LLM TIA evidence generated under: %s\n' "$RUN_ROOT"
