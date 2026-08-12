#!/usr/bin/env bash
set -euo pipefail

# task061 综合核验：SCC 审查 FAIL 残留与跨模块防护
# 覆盖：IssueItem 平台级守卫、各模块 _issue 空值守卫、SCC 全链路、
#       以及 async task 状态持久化（阶段四）。

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

if command -v uv >/dev/null 2>&1; then
  PY=(uv run --frozen python)
else
  PY=(python3)
fi

PASSED=0
FAILED=0

check() {
  local name="$1"
  shift
  if "${PY[@]}" -c "$@" >/dev/null 2>&1; then
    echo "[PASS] ${name}"
    PASSED=$((PASSED + 1))
  else
    echo "[FAIL] ${name}" >&2
    FAILED=$((FAILED + 1))
  fi
}

echo "=== task061 综合核验 ==="
echo ""

# 1. IssueItem 平台级守卫（阶段一）
check "IssueItem 空串被守卫" '
from backend.common.workflow import IssueItem
i = IssueItem(issue_id="V1", title="T", description="D", category="other", severity="LOW", recommended_action="")
assert i.recommended_action and i.recommended_action.strip()
i2 = IssueItem(issue_id="V2", title="T", description="D", category="other", severity="LOW", recommended_action="   \t ")
assert i2.recommended_action.strip()
i3 = IssueItem(issue_id="V3", title="T", description="D", category="other", severity="LOW", recommended_action="正常建议")
assert i3.recommended_action == "正常建议"
print("ok")
'

# 2. SCC 全链路（阶段一 + 原触发点）
check "SCC 全链路空 recommendation 被守卫" '
from backend.domains.eu.scc_review.issue_builder import build_eu_scc_issues
from backend.domains.eu.scc_review.schema import SCCFinding, SCCRuleEngineResult
f = SCCFinding(finding_id="T", location="C15", severity="HIGH", risk_analysis="T", recommendation="")
r = SCCRuleEngineResult(all_findings=[f], overall_rating="HIGH")
issues = build_eu_scc_issues([], r, [])
assert issues, "expected at least one issue"
assert all(i.recommended_action and i.recommended_action.strip() for i in issues)
print("ok")
'

# 3. DPIA _issue 守卫
check "DPIA _issue 空值守卫" '
from backend.domains.eu.dpia.issue_builder import _issue
i = _issue("D1", "T", "D", "other", "LOW", [], [], "", ["ch1"])
assert i.recommended_action and i.recommended_action.strip()
print("ok")
'

# 4. EO14117 _issue 守卫
check "EO14117 _issue 空值守卫" '
from backend.domains.us.eo14117.issue_builder import _issue
i = _issue("E1", "T", "D", "other", "LOW", [], [], "", ["ch1"])
assert i.recommended_action and i.recommended_action.strip()
print("ok")
'

# 5. PIPIA _issue 守卫
check "PIPIA _issue 空值守卫" '
from backend.domains.cn.pipia.service import PIPIAService
i = PIPIAService._issue("P1", "T", "D", "other", "LOW", "")
assert i.recommended_action and i.recommended_action.strip()
print("ok")
'

# 6. Security Assessment _issue 守卫
check "Security Assessment _issue 空值守卫" '
from backend.domains.cn.security_assessment.issue_builder import _issue
i = _issue("S1", "T", "D", "other", "LOW", [], [], "", ["ch1"])
assert i.recommended_action and i.recommended_action.strip()
print("ok")
'

# 7. async task 状态持久化（阶段四）
check "async task 状态持久化" '
import os, tempfile, time
from backend.core.db import build_engine, build_session_factory, init_db
from backend.common.tasks.manager import InMemoryTaskManager, configure_task_persistence
from backend.models.async_task import AsyncTaskModel
tmp = tempfile.mkdtemp()
engine = build_engine("sqlite:///" + os.path.join(tmp, "t.db"))
init_db(engine)
configure_task_persistence(build_session_factory(engine))
m = InMemoryTaskManager(module="eu_scc")
acc = m.submit(lambda: {"output_files": {"markdown": "/tmp/r.md"}})
deadline = time.time() + 5
while time.time() < deadline:
    if m.get_or_raise(acc.task_id).state in {"COMPLETED", "FAILED"}:
        break
    time.sleep(0.02)
factory = build_session_factory(engine)
with factory() as db:
    row = db.get(AsyncTaskModel, acc.task_id)
    assert row is not None and row.status == "COMPLETED"
print("ok")
'

echo ""
echo "=== task061 核验完成：${PASSED} PASS / ${FAILED} FAIL ==="

if [[ "${FAILED}" -gt 0 ]]; then
  exit 1
fi
