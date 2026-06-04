from __future__ import annotations

from typing import Any


def _read_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _read_output_files(payload: dict[str, Any]) -> list[str]:
    files: list[str] = []
    output_files = payload.get("output_files")
    if isinstance(output_files, dict):
        for value in output_files.values():
            if isinstance(value, str) and value.strip():
                files.append(value)
    report_path = payload.get("report_path")
    if isinstance(report_path, str) and report_path.strip() and report_path not in files:
        files.insert(0, report_path)
    return files


def _build_risks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    risk_level = payload.get("risk_level")
    if isinstance(risk_level, str) and risk_level.strip():
        risks.append({"severity": risk_level.upper(), "count": 1})

    overall_rating = payload.get("overall_rating")
    if isinstance(overall_rating, str) and overall_rating.strip():
        risks.append({"severity": overall_rating.upper(), "count": 1})

    traffic = payload.get("overall_traffic_light")
    if isinstance(traffic, str) and traffic.strip():
        risks.append({"severity": traffic.upper(), "count": 1})

    findings = payload.get("findings")
    if isinstance(findings, list):
        high_count = 0
        medium_count = 0
        low_count = 0
        for item in findings:
            if not isinstance(item, dict):
                continue
            severity = str(item.get("risk_level") or item.get("severity") or "").upper()
            if severity == "HIGH":
                high_count += 1
            elif severity == "MEDIUM":
                medium_count += 1
            elif severity == "LOW":
                low_count += 1
        for severity, count in (("HIGH", high_count), ("MEDIUM", medium_count), ("LOW", low_count)):
            if count:
                risks.append({"severity": severity, "count": count})

    gap_items = payload.get("gap_items")
    if isinstance(gap_items, list):
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for item in gap_items:
            if isinstance(item, dict):
                level = str(item.get("risk_level", "")).upper()
                if level in counts:
                    counts[level] += 1
        for severity, count in counts.items():
            if count:
                risks.append({"severity": severity, "count": count})

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in risks:
        key = (str(item["severity"]), int(item["count"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def build_success_events(module: str, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    files = _read_output_files(payload)
    notices = _read_string_list(payload.get("consistency_issues"))[:5]
    risks = _build_risks(payload)
    result_count = len(payload.get("chapters", [])) if isinstance(payload.get("chapters"), list) else 0

    final_payload = {
        "summary": f"{module} 执行完成",
        "detail": {
            "module": module,
            "output_files": payload.get("output_files", {}),
            "output_file_count": len(files),
            "consistency_issue_count": len(_read_string_list(payload.get("consistency_issues"))),
        },
    }
    brief_payload = {
        "summary": f"{module} 执行完成",
        "detail": {
            "conclusion": f"{module} 工作流已执行完成，并生成可交付结果。",
            "files": files,
            "risks": risks,
            "next_steps": [
                "复核生成文件与风险摘要，确认是否需要人工补充。",
                "检查结果中的一致性提示与待核验事项。",
            ],
            "stats": {
                "output_files_count": len(files),
                "chapter_count": result_count,
            },
            "notices": notices,
        },
    }
    return final_payload, brief_payload


def build_failure_events(module: str, error: str) -> tuple[dict[str, Any], dict[str, Any]]:
    final_payload = {
        "summary": f"{module} 执行失败",
        "detail": {
            "module": module,
            "error": error,
        },
    }
    brief_payload = {
        "summary": f"{module} 执行失败",
        "detail": {
            "conclusion": f"{module} 本次执行失败，需要检查错误并重新运行。",
            "files": [],
            "risks": [{"severity": "ERROR", "count": 1}],
            "next_steps": [
                "查看失败原因并修正输入或服务配置。",
                "重新执行工作流并确认最终产物是否生成。",
            ],
            "stats": {
                "output_files_count": 0,
            },
            "notices": [error],
        },
    }
    return final_payload, brief_payload
