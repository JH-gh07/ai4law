"""BCRReportRenderer — 11-section professional BCR review report."""

from __future__ import annotations

from backend.modules.bcr.schema import BCRFinding, BCRTypeClassification


class BCRReportRenderer:
    def build_sections(
        self, type_class: BCRTypeClassification,
        findings: list[BCRFinding], missing: list[str],
        rating: str, score: float, metadata: dict,
    ) -> list[tuple[str, list[str]]]:
        s: list[tuple[str, list[str]]] = []

        # 一、报告摘要
        s.append(("一、报告摘要", [
            f"BCR 类型：{type_class.actual_bcr_type} (声明为 {type_class.declared_bcr_type})",
            f"类型一致性：{type_class.type_consistency}",
            f"综合评级：{rating} ({score}/100)",
            f"发现问题：{len(findings)} 项 | 缺失强制项：{len(missing)} 项",
        ]))

        # 二、BCR 类型与适用路径判断
        s.append(("二、BCR 类型与适用路径判断", [
            f"声明的 BCR 类型：{type_class.declared_bcr_type}",
            f"检测到的 BCR 类型：{type_class.actual_bcr_type}",
            f"一致性：{type_class.type_consistency}",
            f"风险等级：{type_class.risk_level}",
        ] + [f"证据：{e}" for e in type_class.evidence] + (
            [f"建议：{type_class.recommendation}"] if type_class.recommendation else []
        )))

        # 三、文档结构完整性检查
        s.append(("三、文档结构完整性检查", [
            f"缺失强制要素：{len(missing)} 项",
        ] + [f"  - {m}" for m in missing] or ["所有强制要素均已覆盖。"]))

        # 四、GDPR 第47条强制要素审查
        high = [f for f in findings if f.risk_level == "HIGH"]
        med = [f for f in findings if f.risk_level == "MEDIUM"]
        low = [f for f in findings if f.risk_level == "LOW"]
        s.append(("四、GDPR 第47条强制要素审查", [
            f"高风险发现：{len(high)} 项",
            f"中风险发现：{len(med)} 项",
            f"低风险发现：{len(low)} 项",
        ]))

        # 五、第三国法律评估与政府访问请求
        tia_items = [f for f in findings if "third country" in f.requirement_id.lower() or "tia" in f.requirement_id.lower()
                     or "government" in f.requirement_id.lower()]
        s.append(("五、第三国法律评估与政府访问请求", [
            f"{f.title} [{'HIGH' if f.risk_level == 'HIGH' else 'MEDIUM' if f.risk_level == 'MEDIUM' else 'LOW'}]"
            for f in tia_items
        ] or ["未发现 TIA / 政府访问相关问题。"]))

        # 六、Onward Transfer 审查
        onward = [f for f in findings if "onward" in f.requirement_id.lower() or "transfer" in f.requirement_id.lower()]
        s.append(("六、Onward Transfer 审查", [
            f"{f.title} [{'HIGH' if f.risk_level == 'HIGH' else 'MEDIUM' if f.risk_level == 'MEDIUM' else 'LOW'}]"
            for f in onward
        ] or ["未发现 Onward Transfer 问题。"]))

        # 七、条款级问题清单
        if findings:
            issue_lines: list[str] = []
            for i, f in enumerate(findings, 1):
                issue_lines.extend([
                    f"--- 问题 {i} ---",
                    f"编号：{f.finding_id}",
                    f"审查要素：{f.requirement_id}",
                    f"风险等级：{f.risk_level} | 标题：{f.title}",
                    f"发现：{f.finding}",
                ] + ([f"法规依据：{'；'.join(f.legal_basis)}"] if f.legal_basis else []) +
                    [f"建议：{f.recommendation}"] +
                    ([f"建议修改文本：{f.suggested_revision}"] if f.suggested_revision else []) +
                    [f"置信度：{f.review_confidence}"]
                )
            s.append(("七、条款级问题清单", issue_lines))
        else:
            s.append(("七、条款级问题清单", ["未发现条款级问题。"]))

        # 八、核心风险与整改优先级
        s.append(("八、核心风险与整改优先级", [
            "高风险项（需立即整改）：",
            *[f"  - {f.title}" for f in high],
            "中风险项（建议整改）：",
            *[f"  - {f.title}" for f in med],
        ]))

        # 九、法规与监管依据汇总
        all_refs: set[str] = set()
        for f in findings:
            for lb in f.legal_basis:
                all_refs.add(lb)
        s.append(("九、法规与监管依据汇总", [f"  - {r}" for r in sorted(all_refs)] or ["未检索到法规依据。"]))

        # 十、建议补充材料
        s.append(("十、建议补充材料", [
            "- BCR 成员名单",
            "- 内部约束协议",
            "- 投诉处理流程",
            "- 审计与培训制度",
            "- TIA / 第三国法律评估文件",
        ]))

        # 十一、审查边界说明
        s.append(("十一、审查边界说明", [
            "1. 本报告由自动化 BCR 审查系统生成，仅供参考，不构成正式法律意见。",
            f"2. 审查完成时间：{metadata.get('completed_at', '未知')}",
            f"3. 审查模式：{metadata.get('review_mode', 'unknown')}",
            "4. 审查范围限于已上传 BCR 文档的文本内容。",
        ]))

        return s
