"""Agent 1 (P0): ImportantDataAgent — identify whether data may constitute "important data" under Chinese law.

Trigger: q2_has_important_data == "unknown" OR m3_processes_important_data == "unknown"
"""

from __future__ import annotations

from backend.modules.diagnosis.agents import DiagAgentBase

_IMPORTANT_DATA_CONTEXTS = {
    "医疗": ["patient records", "罕见病", "基因", "clinical trial", "genetic", "genomic", "健康", "病历", "患者"],
    "金融": ["transaction records", "credit", "银行", "证券", "保险", "金融", "支付流水", "征信"],
    "汽车": ["自动驾驶", "VIN", "车辆轨迹", "地图", "high-precision map", "路网", "车联网"],
    "工业": ["工业运行", "SCADA", "PLC", "工业控制", "产能", "能耗"],
    "能源": ["能源调度", "电网", "油气", "电力", "pipeline", "石油"],
    "通信": ["mass user data", "大规模用户", "通信内容", "信令"],
    "科研": ["基因", "population data", "族群", "人类遗传", "遗传资源"],
    "政务": ["政府", "公共安全", "交通", "应急", "地理信息", "测绘"],
}

_HEURISTIC_WEIGHTS = {
    "population_scale": 3,     # 万人级以上
    "industry_sensitive": 2,   # 金融/医疗/汽车/工业/能源
    "genetic_related": 3,      # 基因/遗传/族群
    "government_related": 3,   # 政府/公共安全/地理
    "cross_border_purpose": 1, # 国际合作研究
    "regional_systematic": 2,  # 区域性/系统性
}


class ImportantDataAgent(DiagAgentBase):
    agent_name = "diagnosis_important_data"
    max_tokens = 500

    def run(self, industry: str = "", data_desc: str = "",
            data_types: list[str] | None = None,
            important_data_types: list[str] | None = None,
            purpose: str = "", volume_range: str = "",
            processes_important_data: str = "") -> dict:
        """Assess whether the described data is likely "important data".

        Returns structured assessment with suggested value for q2_has_important_data.
        LLM unavailable → rule-based heuristic.
        """
        types = data_types or []
        imp_types = important_data_types or []
        combined = f"{industry} {' '.join(types)} {data_desc} {purpose} {volume_range}".lower()

        # ── Heuristic scoring ──
        reasons: list[str] = []
        score = 0

        # Explicit flag
        if processes_important_data == "yes" or imp_types:
            reasons.append("用户明确标注涉及重要数据")
            score += 5

        # Industry match
        for ind_key, keywords in _IMPORTANT_DATA_CONTEXTS.items():
            if ind_key in industry:
                reasons.append(f"行业属于{ind_key}高敏领域")
                score += _HEURISTIC_WEIGHTS["industry_sensitive"]
                break

        # Keyword match
        for ind_key, keywords in _IMPORTANT_DATA_CONTEXTS.items():
            for kw in keywords:
                if kw.lower() in combined:
                    reasons.append(f"数据描述匹配'{kw}'({ind_key})")
                    score += 1
                    break

        # Population scale
        if any(w in volume_range for w in ("1000万", "100-1000万")):
            reasons.append("数据规模达千万/百万级")
            score += _HEURISTIC_WEIGHTS["population_scale"]
        elif any(w in combined for w in ("万人", "万名", "10000", "万例")):
            reasons.append("数据涉及万人以上群体")
            score += _HEURISTIC_WEIGHTS["population_scale"]

        # Genetic / genomic
        if any(kw in combined for kw in ("基因", "genetic", "genomic", "dna", "rna", "遗传")):
            reasons.append("涉及基因/遗传数据")
            score += _HEURISTIC_WEIGHTS["genetic_related"]

        # Government / public safety
        if any(kw in combined for kw in ("政府", "公共安全", "地理", "测绘", "government", "public safety")):
            reasons.append("涉及政府/公共安全/地理信息数据")
            score += _HEURISTIC_WEIGHTS["government_related"]

        # Determine result
        if score >= 5:
            result = "likely_important_data"
            suggested = "yes"
            confidence = min(0.9, 0.5 + score * 0.08)
        elif score >= 3:
            result = "possible_important_data"
            suggested = "yes"
            confidence = 0.65
        elif score >= 1:
            result = "unlikely_important_data"
            suggested = "unknown"
            confidence = 0.5
        else:
            result = "insufficient_information"
            suggested = "unknown"
            confidence = 0.4

        # ── LLM refinement if available ──
        agent_result = self._call_llm(
            f"""Determine if the following data may constitute "重要数据" under Chinese law.

Industry: {industry}
Data description: {data_desc}
Data types: {types}
Purpose: {purpose}
Volume: {volume_range}
Heuristic result: {result} (score={score}, reasons={reasons})

Return JSON:
{{
  "assessment_type": "important_data",
  "result": "likely_important_data|possible_important_data|unlikely_important_data|insufficient_information",
  "suggested_answer": "yes|no|unknown",
  "confidence": 0.0-1.0,
  "matched_features": ["feature1", "feature2"],
  "legal_basis": ["《数据安全法》第21条", "..."],
  "recommended_user_message": "<one sentence guidance>"
}}"""
        )

        if agent_result:
            return agent_result

        # Fallback
        return {
            "assessment_type": "important_data",
            "result": result,
            "suggested_answer": suggested,
            "confidence": confidence,
            "matched_features": reasons or ["无明显匹配特征"],
            "legal_basis": ["《数据安全法》第21条", "《促进和规范数据跨境流动规定》第7条"],
            "recommended_user_message": (
                f"基于审慎原则，建议按{'涉及' if suggested == 'yes' else '暂不涉及'}重要数据处理。"
                f"最终仍应结合主管部门目录确认。" if reasons
                else "当前信息不足以判断是否涉及重要数据，请补充数据性质、行业领域和数据规模后复判。"
            ),
            "heuristic_score": score,
        }
