"""Agent 6: Expression calibration — converts internal risk language to external report language."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CalibrationChange:
    location: str
    original: str
    problem: str
    calibrated: str
    reason: str


@dataclass
class CalibrationResult:
    changes: list[CalibrationChange] = field(default_factory=list)
    internal_leak_detected: list[str] = field(default_factory=list)
    passed: bool = True


class ExpressionCalibrationAgent:
    """Calibrates external report expressions — converts internal risk language to
    regulatory-appropriate external language."""

    # Over-commitment patterns (too positive for external reports)
    OVER_COMMITMENT_PATTERNS = [
        (r"(已\s*)?(完全|充分|全面|完善)(地\s*)?(具备|建立|实现|拥有|保障|证明)", "过度承诺"),
        (r"(不\s*)?(存在|涉及|构成)(任何\s*)?(合规\s*)?(风险|违规|问题|障碍)", "过度否定风险"),
        (r"材料\s*(齐全|完备|完整|充分)", "证据过度肯定"),
        (r"(完全|已经|已)(满足|符合|达到|实现)(合规|监管|法律|标准)要求", "合规结论过度"),
        (r"(数据\s*)?(安全|保护|合规)(体系|能力|机制)(已经|已\s*)?(完善|健全|充分|到位)", "安全能力过度肯定"),
        (r"(不存在|没有)(重要数据|敏感个人信息|安全风险)", "风险否认过度"),
        (r"(可以|能够|应当)(直接|立即)(申报|提交|备案)", "申报建议过于肯定"),
        (r"(违法|违规|非法)(处理|传输|收集|使用)", "违法定性"),
    ]

    # Internal language that shouldn't leak to external reports
    INTERNAL_PATTERNS = [
        r"系统\s*(判断|认为|无法确认|检测到)",
        r"根据\s*(规则|算法|AI|模型)",
        r"置信度\s*(低|不足|较低)",
        r"保守\s*(估计|策略|判断)",
        r"材料\s*(严重\s*)?(缺失|不足|不够)",
    ]

    def run(self, report_text: str) -> CalibrationResult:
        """Scan external report for over-commitment and internal leakage."""
        result = CalibrationResult()

        # Check over-commitment
        for pattern, problem_type in self.OVER_COMMITMENT_PATTERNS:
            for m in re.finditer(pattern, report_text):
                original = m.group(0)
                start = max(0, m.start() - 20)
                end = min(len(report_text), m.end() + 30)
                context = report_text[start:end]

                calibrated = self._calibrate(original, problem_type)
                result.changes.append(CalibrationChange(
                    location=f"position {m.start()}",
                    original=original,
                    problem=problem_type,
                    calibrated=calibrated,
                    reason=f"对外报告不应使用'{problem_type}'类表述",
                ))

        # Check internal leakage
        for pattern in self.INTERNAL_PATTERNS:
            for m in re.finditer(pattern, report_text):
                result.internal_leak_detected.append(m.group(0))

        result.passed = len(result.changes) == 0 and len(result.internal_leak_detected) == 0
        return result

    @staticmethod
    def _calibrate(text: str, problem_type: str) -> str:
        """Replace over-commitment with regulatory-appropriate language."""
        replacements = {
            "已充分证明": "提供了相关材料佐证",
            "完全符合": "在现有材料条件下基本满足",
            "已完全建立": "已实施相关措施",
            "材料齐全": "已提供初步材料",
            "已满足合规要求": "在现有材料条件下基本符合相关要求",
            "不存在风险": "当前材料下未发现直接触发项",
            "安全保障能力完善": "已采取安全保障措施",
            "可以直接申报": "建议在补充完善后提交申报",
            "不存在重要数据": "用户声明不涉及重要数据",
            "不存在敏感个人信息": "用户声明不涉及敏感个人信息",
        }
        for orig, replacement in replacements.items():
            if orig in text:
                return replacement
        return f"在现有材料条件下，{text}（建议补充进一步佐证材料）"

    def apply_calibration(self, report_text: str) -> str:
        """Apply all calibrations to the report text."""
        result = self.run(report_text)
        calibrated_text = report_text
        for change in result.changes:
            if change.original in calibrated_text:
                calibrated_text = calibrated_text.replace(change.original, change.calibrated)
        return calibrated_text
