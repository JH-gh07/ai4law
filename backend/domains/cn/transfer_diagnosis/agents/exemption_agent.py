"""Agent 4 (P3): ExemptionAgent — assess whether transfer scenario qualifies for exemption.

Trigger: q6_scenario == "other" OR user is uncertain about exemption applicability.
Helps avoid over-conservatively routing to SCC/certification when exemption may apply.
"""

from __future__ import annotations

from backend.domains.cn.transfer_diagnosis.agents import DiagAgentBase

_EXEMPTION_HEURISTICS = {
    "contract_performance": {
        "strong_signals": [
            "跨境购物", "海淘", "跨境支付", "国际机票", "酒店预订",
            "签证", "留学申请", "考试报名", "跨境寄递", "国际物流",
            "用户主动发起", "消费者个人", "为完成交易",
        ],
        "weak_signals": [
            "售后服务", "退换货", "跨境客服", "账户管理",
        ],
        "counter_signals": [
            "营销", "推荐", "算法", "画像", "数据分析",
            "广告", "精准推送", "二次使用",
        ],
    },
    "hr_management": {
        "strong_signals": [
            "员工", "薪酬", "绩效", "考勤", "入职",
            "集团内部", "母公司", "子公司", "关联公司",
            "劳动规章", "集体合同",
        ],
        "counter_signals": [
            "外包", "供应商", "第三方服务",
        ],
    },
    "emergency": {
        "strong_signals": [
            "紧急", "生命", "健康", "安全", "财产",
            "不可抗力", "自然灾害", "事故",
        ],
    },
    "legal_duty": {
        "strong_signals": [
            "法定", "监管要求", "司法协助", "行政执法",
            "反洗钱", "税务申报", "证券披露",
        ],
    },
}


class ExemptionAgent(DiagAgentBase):
    agent_name = "diagnosis_exemption"
    max_tokens = 500

    def run(self, scenario: str = "other", purpose: str = "",
            data_desc: str = "", receiver_type: str = "",
            receiver_name: str = "", is_intra_group: bool = False,
            pii_count: int = 0, spi_count: int = 0) -> dict:
        """Assess possible exemption scenarios."""
        combined = f"{purpose} {data_desc} {receiver_name}".lower()

        candidates: list[dict] = []

        # ── Check each exemption type heuristically ──
        for ex_type, config in _EXEMPTION_HEURISTICS.items():
            strong = sum(1 for s in config["strong_signals"] if s in combined)
            weak = sum(1 for s in config.get("weak_signals", []) if s in combined)
            counter = sum(1 for s in config.get("counter_signals", []) if s in combined)

            if strong >= 1 and counter == 0:
                candidates.append({
                    "type": ex_type,
                    "confidence": min(0.85, 0.5 + strong * 0.15),
                    "missing_questions": self._missing_questions(ex_type),
                })
            elif strong >= 1 and counter >= 1:
                candidates.append({
                    "type": ex_type,
                    "confidence": 0.4,
                    "missing_questions": [
                        f"存在反信号 '{', '.join(config['counter_signals'][:2])}'，请确认",
                        *self._missing_questions(ex_type),
                    ],
                })
            elif weak >= 2 and counter == 0 and is_intra_group:
                candidates.append({
                    "type": ex_type,
                    "confidence": 0.55,
                    "missing_questions": self._missing_questions(ex_type),
                })

        # Sort by confidence descending
        candidates.sort(key=lambda c: c["confidence"], reverse=True)

        # ── LLM refinement ──
        agent_result = self._call_llm(
            f"""Assess whether this data transfer may qualify for exemption under Chinese law.

Scenario: {scenario}
Purpose: {purpose}
Data: {data_desc}
Receiver: {receiver_name} (type={receiver_type}, intra_group={is_intra_group})
PII: {pii_count}, SPI: {spi_count}
Heuristic candidates: {candidates}

Return JSON:
{{
  "candidate_exemptions": [
    {{"type": "contract_performance|hr_management|emergency|legal_duty",
      "confidence": 0.0-1.0,
      "missing_questions": ["question to clarify"]}}
  ],
  "recommended_next_question": "<key question to ask user>",
  "suggested_scenario": "if likely exempt"
}}"""
        )

        if agent_result:
            return agent_result

        return {
            "candidate_exemptions": candidates,
            "recommended_next_question": (
                candidates[0]["missing_questions"][0]
                if candidates and candidates[0].get("missing_questions")
                else "请确认本次数据传输是否属于为履行与个人的合同所必需，或属于集团内部人力资源管理？"
            ),
            "no_exemption_likely": len(candidates) == 0,
        }

    @staticmethod
    def _missing_questions(ex_type: str) -> list[str]:
        q_map = {
            "contract_performance": [
                "本次出境是否为履行用户主动发起的跨境购物/支付/寄递/预订合同所必需？",
                "如果不向境外提供该数据，是否无法完成合同履行？",
                "数据是否仅用于合同履行目的，不用于后续营销或算法优化？",
            ],
            "hr_management": [
                "是否已依法制定劳动规章制度或签订集体合同？",
                "数据出境是否仅限于集团内部人力资源管理所必需？",
                "是否已向员工告知数据出境情况？",
            ],
            "emergency": [
                "是否属于紧急情况下为保护自然人生命、健康或财产安全所必需？",
                "是否无法事先取得个人同意？",
            ],
            "legal_duty": [
                "数据出境是否为履行法定职责或法定义务所必需？",
                "是否有明确的法规条文要求向境外提供该数据？",
            ],
        }
        return q_map.get(ex_type, ["请补充更多业务细节"])
