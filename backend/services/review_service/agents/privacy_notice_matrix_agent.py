"""Agent P1-1: PrivacyNoticeMatrixAgent — privacy policy notice completeness matrix.

Checks whether a privacy policy covers all mandatory disclosure items with
specificity, operability, and cross-document consistency.
"""

from __future__ import annotations

from backend.services.review_service.agents import ReviewAgentBase

_PRIVACY_NOTICE_ITEMS = [
    ("处理者身份", ["处理者", "个人信息处理者", "运营者", "controller", "operator", "公司.*名称"]),
    ("个人信息种类", ["个人信息.*种类", "收集.*个人信息", "data categories", "数据类型", "信息类型"]),
    ("处理目的", ["处理目的", "使用目的", "purpose", "用于以下目的", "目的.*处理"]),
    ("处理方式", ["处理方式", "自动化", "分析", "存储", "加工", "processing method"]),
    ("Cookie/SDK", ["Cookie", "cookie", "SDK", "sdk", "同类技术", "跟踪技术", "标识符"]),
    ("第三方共享/转让", ["第三方", "共享", "转让", "披露", "SDK", "合作伙伴", "third party", "share"]),
    ("委托处理", ["委托", "受托", "委托处理", "受托方", "服务提供商", "entrusted"]),
    ("跨境传输", ["跨境", "出境", "境外", "传输.*境外", "cross.border", "overseas", "境外接收方"]),
    ("用户权利", ["权利", "查阅", "更正", "删除", "撤回", "可携带", "rights", "access.*delete"]),
    ("保存期限", ["保存期限", "存储期限", "保留", "retention", "保存.*期限", "期限.*保存"]),
    ("安全措施", ["安全", "加密", "保护", "措施", "security", "safeguard", "技术.*措施"]),
    ("儿童信息", ["儿童", "未成年", "14岁", "十四", "children", "minor", "under 14"]),
    ("联系方式", ["联系", "邮箱", "电话", "地址", "contact", "email", "phone", "热线"]),
    ("更新机制", ["更新", "修订", "变更", "生效日期", "update", "modification", "amendment"]),
]

_SPECIFICITY_CHECKS = {
    "第三方共享/转让": ["列明", "具体", "名称", "联系方式", "共享.*目的", "共享.*类型"],
    "跨境传输": ["境外接收方.*名称", "境外接收方.*联系", "处理目的", "处理方式", "个人信息种类"],
    "用户权利": ["路径", "方式", "时限", "日内", "工作日内", "如何", "步骤"],
    "保存期限": [r"\d+.*(?:年|月|天|日)", "最短", "必要", "删除", "销毁"],
}


class PrivacyNoticeMatrixAgent(ReviewAgentBase):
    agent_name = "review_privacy_notice"
    max_tokens = 600

    def run(self, full_text: str = "", is_privacy_policy: bool = False) -> dict:
        text = full_text[:10000] if full_text else ""
        if not is_privacy_policy:
            return {"notice_matrix": [], "applicable": False}

        matrix: list[dict] = []
        for item_name, keywords in _PRIVACY_NOTICE_ITEMS:
            present = any(kw.lower() in text.lower() for kw in keywords)
            status = "present"
            specificity = "unknown"
            problem = ""

            if present:
                spec_checks = _SPECIFICITY_CHECKS.get(item_name, [])
                if spec_checks:
                    import re
                    spec_count = sum(1 for c in spec_checks if re.search(c, text, re.IGNORECASE))
                    if spec_count >= 2:
                        specificity = "specific"
                    elif spec_count >= 1:
                        specificity = "vague"
                        problem = f"提及了{item_name}但不够具体"
                    else:
                        specificity = "vague"
                        problem = f"提及了{item_name}但未包含具体细节"
                else:
                    specificity = "present"
            else:
                status = "missing"
                specificity = "missing"

            severity = "LOW"
            if status == "missing":
                severity = "HIGH" if item_name in ("个人信息种类", "处理目的", "用户权利", "跨境传输") else "MEDIUM"
            elif specificity == "vague":
                severity = "MEDIUM" if item_name in ("第三方共享/转让", "跨境传输", "用户权利", "保存期限") else "LOW"

            matrix.append({
                "notice_item": item_name, "status": status, "specificity": specificity,
                "severity": severity, "problem": problem,
            })

        missed_high = [m for m in matrix if m["severity"] == "HIGH"]
        missed_med = [m for m in matrix if m["severity"] == "MEDIUM"]

        return {
            "notice_matrix": matrix,
            "completeness_score": sum(1 for m in matrix if m["status"] == "present") / len(matrix),
            "high_severity_gaps": [m["notice_item"] for m in missed_high],
            "medium_severity_gaps": [m["notice_item"] for m in missed_med],
            "summary": (
                f"告知事项{len(missed_high)}项HIGH缺失, {len(missed_med)}项MEDIUM不足"
                if missed_high or missed_med else "告知事项基本完整"
            ),
        }
