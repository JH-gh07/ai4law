import json
import re
from pathlib import Path

from backend.common.llm.client import LLMClient
from backend.common.risk.scoring import risk_level
from backend.core.settings import get_settings
from backend.common.trace.recorder import TraceRecorder
from backend.modules.diagnosis.schema import DiagnosisAnswers, DiagnosisResult
from backend.modules.diagnosis.agents import create_diag_agents


_RATIONALE_I18N = {
    "CIIO must apply for security assessment": "企业被识别为关键信息基础设施运营者，应优先走安全评估路径。",
    "Important data export must apply for security assessment": "涉及重要数据出境，按监管要求应优先走安全评估路径。",
    "PII count >= 1,000,000 must apply for security assessment": "个人信息处理规模达到法定门槛，应优先走安全评估路径。",
    "Sensitive PII count >= 10,000 must apply for security assessment": "敏感个人信息处理规模达到法定门槛，应优先走安全评估路径。",
    "Threshold not reached for mandatory security assessment.": "未触发强制安全评估门槛，可走标准合同备案或认证路径。",
}


class DiagnosisService:
    def __init__(self, tree_path: str | None = None) -> None:
        self.tree_path = tree_path or str(Path(__file__).with_name("decision_tree.json"))
        self._tree = self._load_tree(self.tree_path)
        self._llm_client = LLMClient(get_settings())
        self.agents = create_diag_agents(self._llm_client)

    @staticmethod
    def _load_tree(tree_path: str) -> dict:
        with open(tree_path, "r", encoding="utf-8") as fp:
            return json.load(fp)

    def evaluate(self, answers: DiagnosisAnswers, *, trace: TraceRecorder | None = None) -> DiagnosisResult:
        answers = self._normalize_answers(answers)

        if trace:
            trace.record("status", {"summary": "开始路径诊断", "detail": {"module": "diagnosis"}})

        # ── Agent-assisted fact clarification for unknown fields ──
        agent_trace: dict = {}
        payload = answers.model_dump()

        # Agent 2 (P0): ImportantDataAgent — when q2 is still unknown
        if answers.q2_has_important_data.value == "unknown":
            imp_result = self.agents["important_data"].run(
                industry=answers.m1_industry,
                data_desc=f"{answers.q8_purpose} {str(answers.m3_personal_info_types)}",
                data_types=list(answers.m3_personal_info_types or []),
                important_data_types=list(answers.m3_important_data_types or []),
                purpose=answers.q8_purpose,
                volume_range=str(answers.m3_data_volume_range or ""),
                processes_important_data=str(answers.m3_processes_important_data or ""),
            )
            if imp_result:
                if trace:
                    trace.record("thought", {"summary": "重要数据分析 Agent 完成"})
                agent_trace["important_data"] = imp_result
                suggested = imp_result.get("suggested_answer", "unknown")
                if suggested in ("yes", "no"):
                    payload["q2_has_important_data"] = suggested
                    answers = DiagnosisAnswers(**payload)

        # Agent 3 (P2): PIClassifyAgent — when q5 is still unknown
        if answers.q5_no_personal_info.value == "unknown":
            pi_result = self.agents["pi_classify"].run(
                data_desc=f"{answers.q8_purpose} {str(answers.m3_personal_info_types)}",
                personal_info_types=list(answers.m3_personal_info_types or []),
                sensitive_info_types=list(answers.m3_sensitive_info_types or []),
                anonymization_desc=str(answers.m3_retention_desc or ""),
                processes_personal_info=str(answers.m3_processes_personal_info or ""),
                industry=answers.m1_industry,
                use_case=str(answers.q6_scenario.value),
            )
            if pi_result:
                if trace:
                    trace.record("thought", {"summary": "个人信息分类 Agent 完成"})
                agent_trace["pi_classify"] = pi_result
                suggested = pi_result.get("suggested_q5_no_personal_info", "unknown")
                if suggested in ("yes", "no"):
                    payload["q5_no_personal_info"] = suggested
                    answers = DiagnosisAnswers(**payload)

        # Agent 4 (P3): ExemptionAgent — when scenario is "other" (may miss exemption)
        if answers.q6_scenario.value == "other":
            ex_result = self.agents["exemption"].run(
                scenario="other",
                purpose=answers.q8_purpose,
                data_desc=str(answers.m3_personal_info_types),
                receiver_type=answers.q7_receiver_type.value,
                receiver_name=str(answers.m4_cross_border_regions or ""),
                is_intra_group=answers.q7_receiver_type.value == "intra_group",
                pii_count=answers.q3_pii_count,
                spi_count=answers.q4_spi_count,
            )
            if ex_result:
                if trace:
                    trace.record("thought", {"summary": "豁免情形分析 Agent 完成"})
                agent_trace["exemption"] = ex_result

        # ── Decision tree ──
        for rule in self._tree["rules"]:
            when = rule["when"]
            if self._rule_match(when, answers):
                if trace:
                    trace.record("final", {"summary": "路径诊断完成", "detail": {"matched_rule": rule.get("id", ""), "recommended_path": rule.get("path", "")}})
                return self._build_rule_result(answers, rule)

        # 明显信息不足时，走 AI 推测路径（并显式标注为推测结论）。
        if self._needs_ai_inference(answers):
            inferred = self._build_ai_inference_result(answers)
            if inferred is not None:
                if trace:
                    trace.record("final", {"summary": "路径诊断完成", "detail": {"mode": "ai_inference", "recommended_path": inferred.recommended_path}})
                return inferred

        # ── Attach agent findings to uncertainty notes ──
        agent_notes: list[str] = []
        if agent_trace.get("important_data"):
            ad = agent_trace["important_data"]
            agent_notes.append(
                f"[Agent] 重要数据辅助判断: {ad.get('result','?')} "
                f"(置信度 {ad.get('confidence',0):.0%}), "
                f"建议值: q2={ad.get('suggested_answer','?')}"
            )
        if agent_trace.get("pi_classify"):
            pd = agent_trace["pi_classify"]
            agent_notes.append(
                f"[Agent] 个人信息辅助判断: {pd.get('personal_information_result','?')}, "
                f"重识别风险: {pd.get('re_identification_risk','?')}"
            )
        if agent_trace.get("exemption"):
            ed = agent_trace["exemption"]
            cands = ed.get("candidate_exemptions", [])
            if cands:
                top = cands[0]
                agent_notes.append(
                    f"[Agent] 豁免情形辅助判断: {top.get('type','?')} "
                    f"(置信度 {top.get('confidence',0):.0%})"
                )

        default = self._tree["default"]
        if trace:
            trace.record("final", {"summary": "路径诊断完成", "detail": {"mode": "default", "recommended_path": default.get("path", "")}})
        return self._build_result(
            answers,
            default["path"],
            default["legal_basis"],
            _RATIONALE_I18N["Threshold not reached for mandatory security assessment."],
            conclusion_source="rule",
            confidence="MEDIUM",
            matched_rule_id="default",
            uncertainty_notes=agent_notes if agent_notes else None,
        )

    @staticmethod
    def _contains_sensitive_personal_info(items: list[str]) -> bool:
        keywords = ("身份证", "人脸", "指纹", "声纹", "健康", "金融", "未成年人", "精准位")
        return any(any(key in item for key in keywords) for item in items)

    @staticmethod
    def _estimate_pii_count(volume_range: str) -> int:
        if volume_range == "1000万条以上":
            return 10_000_000
        if volume_range == "100-1000万条":
            return 2_000_000
        if volume_range == "10-100万条":
            return 300_000
        if volume_range == "10万条以下":
            return 50_000
        return 0

    def _normalize_answers(self, answers: DiagnosisAnswers) -> DiagnosisAnswers:
        payload = answers.model_dump()
        personal_types = [str(item) for item in payload.get("m3_personal_info_types", []) if str(item).strip()]
        sensitive_types = [str(item) for item in payload.get("m3_sensitive_info_types", []) if str(item).strip()]
        important_types = [str(item) for item in payload.get("m3_important_data_types", []) if str(item).strip()]

        has_personal_info = (
            payload.get("m3_processes_personal_info") == "yes"
            or len(personal_types) > 0
        )
        has_sensitive_info = len(sensitive_types) > 0 or self._contains_sensitive_personal_info(personal_types)
        has_important_data = (
            payload.get("m3_processes_important_data") == "yes"
            or len(important_types) > 0
        )

        if payload.get("q2_has_important_data") == "unknown" and has_important_data:
            payload["q2_has_important_data"] = "yes"
        elif payload.get("q2_has_important_data") == "unknown" and not has_important_data and payload.get("m3_processes_important_data") == "no":
            payload["q2_has_important_data"] = "no"

        if payload.get("q5_no_personal_info") == "unknown":
            payload["q5_no_personal_info"] = "yes" if (not has_personal_info and not has_important_data) else "no"

        if int(payload.get("q3_pii_count") or 0) == 0 and has_personal_info:
            payload["q3_pii_count"] = self._estimate_pii_count(str(payload.get("m3_data_volume_range") or ""))

        if int(payload.get("q4_spi_count") or 0) == 0 and has_sensitive_info:
            volume_hint = str(payload.get("m3_data_volume_range") or "")
            payload["q4_spi_count"] = 12_000 if volume_hint in {"1000万条以上", "100-1000万条"} else 2_000

        if payload.get("q7_receiver_type") == "third_party":
            share_to_third_party = payload.get("m4_share_to_third_party") == "yes"
            entrusted_processing = payload.get("m4_entrusted_processing") == "yes"
            if not share_to_third_party and not entrusted_processing:
                payload["q7_receiver_type"] = "intra_group"

        return DiagnosisAnswers(**payload)

    @staticmethod
    def _rule_match(when: dict, answers: DiagnosisAnswers) -> bool:
        if "q1_is_ciio" in when and answers.q1_is_ciio.value not in when["q1_is_ciio"]:
            return False
        if "q2_has_important_data" in when and answers.q2_has_important_data.value not in when["q2_has_important_data"]:
            return False
        if "q3_pii_count_gte" in when and answers.q3_pii_count < int(when["q3_pii_count_gte"]):
            return False
        if "q4_spi_count_gte" in when and answers.q4_spi_count < int(when["q4_spi_count_gte"]):
            return False
        if "q3_pii_count_lt" in when and answers.q3_pii_count >= int(when["q3_pii_count_lt"]):
            return False
        if "q4_spi_count_lt" in when and answers.q4_spi_count >= int(when["q4_spi_count_lt"]):
            return False
        if "q5_no_personal_info" in when and answers.q5_no_personal_info.value not in when["q5_no_personal_info"]:
            return False
        if "q6_scenario" in when and answers.q6_scenario.value not in when["q6_scenario"]:
            return False
        if "q7_receiver_type" in when and answers.q7_receiver_type.value not in when["q7_receiver_type"]:
            return False
        return True

    def _build_rule_result(self, answers: DiagnosisAnswers, rule: dict) -> DiagnosisResult:
        result = self._build_result(
            answers,
            rule["path"],
            rule.get("legal_basis", []),
            rule.get("description", ""),
            conclusion_source="rule",
            confidence="HIGH",
            matched_rule_id=rule.get("id"),
        )
        result.final_explanation = self._build_rule_explanation(result, answers)
        return result

    def _build_rule_explanation(self, result: DiagnosisResult, answers: DiagnosisAnswers) -> str:
        if not self._llm_client.enabled:
            return result.rationale
        user_prompt = (
            "请基于以下规则判定结果，输出2-3句专业中文解释。要求："
            "1) 只能解释，不得改判推荐路径；2) 指出关键触发点；3) 给出一句行动建议。\n"
            f"推荐路径：{result.recommended_path}\n"
            f"风险等级：{result.risk_level}\n"
            f"规则依据：{'；'.join(result.legal_basis)}\n"
            f"判定说明：{result.rationale}\n"
            f"问卷答案：{answers.model_dump_json()}"
        )
        text = self._llm_client.chat(
            system="你是一名中国数据出境合规律师，仅负责解释规则结论，不改判。",
            user=user_prompt,
            temperature=0.2,
            max_tokens=300,
        ).strip()
        return text or result.rationale

    @staticmethod
    def _build_result(
        answers: DiagnosisAnswers,
        recommended_path: str,
        legal_basis: list[str],
        rationale: str,
        conclusion_source: str = "rule",
        confidence: str = "HIGH",
        matched_rule_id: str | None = None,
        uncertainty_notes: list[str] | None = None,
        final_explanation: str = "",
    ) -> DiagnosisResult:
        rationale = _RATIONALE_I18N.get(rationale, rationale)
        level = risk_level(
            is_ciio=answers.q1_is_ciio.value == "yes",
            contains_important_data=answers.q2_has_important_data.value == "yes",
            pii_count=answers.q3_pii_count,
            spi_count=answers.q4_spi_count,
        )
        if recommended_path == "security_assessment":
            action_items = [
                "整理数据出境清单与处理活动映射。",
                "生成《数据出境风险自评估报告》草案并补齐附件。",
                "按属地网信要求提交安全评估申报材料。",
            ]
        else:
            action_items = [
                "在标准合同备案与个人信息保护认证之间确定实施路径。",
                "生成 PIPIA 报告及标准合同配套附件。",
                "准备省级网信备案/留档材料并完成内部审批。",
            ]

        return DiagnosisResult(
            recommended_path=recommended_path,
            legal_basis=legal_basis,
            rationale=rationale,
            action_items=action_items,
            risk_level=level,
            conclusion_source=conclusion_source,
            confidence=confidence,
            matched_rule_id=matched_rule_id,
            final_explanation=final_explanation or rationale,
            uncertainty_notes=uncertainty_notes or [],
        )

    @staticmethod
    def _needs_ai_inference(answers: DiagnosisAnswers) -> bool:
        # 规则无法可靠收敛的典型信号：关键布尔位不确定，且出境规模信息较弱。
        uncertain_flags = (
            answers.q1_is_ciio.value == "unknown"
            or answers.q2_has_important_data.value == "unknown"
            or answers.q5_no_personal_info.value == "unknown"
        )
        weak_volume_signal = answers.q3_pii_count == 0 and answers.q4_spi_count == 0
        # 若问卷明确填写了核心处理事实，不应因 q 字段缺失而轻易走 AI 推测。
        has_structured_signals = (
            answers.m3_processes_personal_info in {"yes", "no"}
            or answers.m3_processes_important_data in {"yes", "no"}
            or len(answers.m3_personal_info_types) > 0
            or len(answers.m3_important_data_types) > 0
        )
        if has_structured_signals and not weak_volume_signal:
            return False
        return uncertain_flags or weak_volume_signal

    def _build_ai_inference_result(self, answers: DiagnosisAnswers) -> DiagnosisResult | None:
        # 检查LLM客户端是否启用
        if not self._llm_client.enabled:
            # 如果LLM客户端未启用，构建一个保守推测结果
            return self._build_result(
                answers,
                recommended_path="scc_or_certification",  # 推荐路径设为标准合同/认证
                legal_basis=self._tree["default"]["legal_basis"],  # 使用默认法律依据
                rationale="当前关键字段存在不确定项，暂按标准合同/认证路径进行保守推测，需人工复核。",  # 推理说明
                conclusion_source="ai_inference",  # 结论来源为AI推理
                confidence="LOW",  # 置信度为低
                matched_rule_id=None,  # 无匹配规则ID
                uncertainty_notes=[  # 不确定性说明
                    "关键字段含 unknown 或缺乏规模信息。",
                    "LLM 未配置，未能生成更细化推测。",
                ],
                final_explanation="该结论为推测结论，不可直接作为最终法律意见，请补充信息后复判。",  # 最终解释
            )
        # 构建提示词，指导AI进行数据跨境合规分析

        prompt = (
            "你是中国数据跨境合规律师。请基于给定问答做“推测结论”，仅在规则不足时使用。"
            "请返回JSON，不要额外文本。字段："
            "recommended_path(仅可为security_assessment/scc_or_certification/exemption),"
            "rationale, risk_level(LOW/MEDIUM/HIGH), legal_basis(string数组), action_items(string数组，最多4条),"
            "confidence(LOW/MEDIUM), uncertainty_notes(string数组), final_explanation。\n"
            f"输入：{answers.model_dump_json(ensure_ascii=False)}"
        )
        raw = self._llm_client.chat(
            system="你是一名严谨的中国数据出境合规律师，只输出JSON。",
            user=prompt,
            temperature=0.1,
            max_tokens=800,
        )
        parsed = self._parse_json_object(raw)
        if not isinstance(parsed, dict):
            return self._build_result(
                answers,
                recommended_path="scc_or_certification",
                legal_basis=self._tree["default"]["legal_basis"],
                rationale="关键字段不完整，已触发AI推测，但解析失败，采用保守推测路径。",
                conclusion_source="ai_inference",
                confidence="LOW",
                uncertainty_notes=["AI 输出无法解析为结构化 JSON。"],
                final_explanation="系统触发了AI推测，但当前仅返回保守建议，请补全信息后重判。",
            )

        path = str(parsed.get("recommended_path") or "scc_or_certification")
        if path not in {"security_assessment", "scc_or_certification", "exemption"}:
            path = "scc_or_certification"
        legal_basis = [str(item) for item in parsed.get("legal_basis", []) if str(item).strip()]
        if not legal_basis:
            legal_basis = self._tree["default"]["legal_basis"]
        action_items = [str(item) for item in parsed.get("action_items", []) if str(item).strip()][:4]
        uncertainty_notes = [str(item) for item in parsed.get("uncertainty_notes", []) if str(item).strip()]
        if not uncertainty_notes:
            uncertainty_notes = ["该结论由AI推测生成，需人工复核。"]
        confidence = str(parsed.get("confidence") or "LOW").upper()
        if confidence not in {"LOW", "MEDIUM"}:
            confidence = "LOW"

        result = self._build_result(
            answers,
            recommended_path=path,
            legal_basis=legal_basis,
            rationale=str(parsed.get("rationale") or "关键字段不完整，系统给出推测结论。"),
            conclusion_source="ai_inference",
            confidence=confidence,
            uncertainty_notes=uncertainty_notes,
            final_explanation=str(
                parsed.get("final_explanation")
                or "本结论为推测结论，请在补充关键字段后再次执行规则判定。"
            ),
        )
        if action_items:
            result.action_items = action_items
        risk = str(parsed.get("risk_level") or "").upper()
        if risk in {"LOW", "MEDIUM", "HIGH"}:
            result.risk_level = risk
        return result

    @staticmethod
    def _parse_json_object(raw: str) -> dict | None:
        text = (raw or "").strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
        # 兼容模型外层包裹说明文字的情况。
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
