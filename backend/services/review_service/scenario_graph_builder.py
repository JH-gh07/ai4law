"""ScenarioGraphBuilder — extract structured actor‑data‑flow‑location graphs.

Upgrades ScenarioExtractor from flat regex facts to a graph of:
  actors (who) → data_flows (what flows where) → processes (actions) → basis (legal grounds)
"""

from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

_OVERSEAS = [
    "新加坡", "香港", "美国", "日本", "韩国", "英国", "德国", "法国",
    "澳大利亚", "印度", "马来西亚", "泰国", "台湾", "开曼",
]
_OVERSEAS_RE = re.compile("|".join(_OVERSEAS))
_ACTIONS = ["传输", "传至", "提供", "共享", "发送", "传递", "存储", "处理",
             "备份", "出境", "委托", "运维", "访问", "分析", "运算"]

_ACTOR_PATTERNS = [
    (re.compile(r"甲方[：:]\s*(.{2,40}?(?:有限公司|股份公司|集团|公司|科技|数据|信息|网络|技术))"), "个人信息处理者/委托方"),
    (re.compile(r"乙方[：:]\s*(.{2,40}?(?:有限公司|股份公司|集团|公司|科技|数据|信息|网络|技术|Pte\s*Ltd|Ltd|LLC|Inc))"), "受托方/接收方"),
    (re.compile(r"(?:委托方|个人信息处理者)[：:]\s*(.{2,40}?(?:有限公司|股份公司|集团|公司))"), "个人信息处理者/委托方"),
    (re.compile(r"(?:受托方|接收方|境外接收方)[：:]\s*(.{2,40}?(?:有限公司|股份公司|集团|公司|Pte\s*Ltd|Ltd|LLC|Inc))"), "受托方/接收方"),
    (re.compile(r"(?:Data Controller|Controller)[：:]\s*(.{2,60}?(?:Ltd|LLC|Inc|Corp|Pte|GmbH|S\.A\.))", re.IGNORECASE), "Controller"),
    (re.compile(r"(?:Data Processor|Processor)[：:]\s*(.{2,60}?(?:Ltd|LLC|Inc|Corp|Pte|GmbH|S\.A\.))", re.IGNORECASE), "Processor"),
]

_DATA_KEYWORDS = [
    "消费记录", "门禁记录", "行踪轨迹", "生物识别", "金融", "健康", "教育",
    "浏览记录", "支付", "身份信息", "通信", "设备信息", "位置", "日志",
    "图书", "借阅", "用户", "个人",
]

_CB_INDICATOR_PATTERNS = [
    r"(?:境外|跨境|数据出境|传输.*境外|出境.*数据|域外)",
    r"(?:服务器|数据|信息).{0,15}(?:新加坡|香港|美国|境外|海外)",
    r"(?:SCC|标准合同|安全评估|保护认证).{0,15}(?:数据传输|数据出境)",
]

_LEGAL_GROUND_PATTERNS = [
    (re.compile(r"(安全评估|数据出境安全评估|通过.*安全评估)"), "安全评估"),
    (re.compile(r"(标准合同|个人信息出境标准合同|SCC|Standard\s*Contractual\s*Clauses)"), "标准合同"),
    (re.compile(r"(保护认证|认证|个人信息保护认证)"), "保护认证"),
    (re.compile(r"(单独同意|取得.*同意|获得.*同意|告知.*同意)"), "单独同意"),
    (re.compile(r"(第13条|履行合同.*必需|法定义务|合法权益)"), "合法性基础"),
]

_UNCERTAIN_PATTERNS = [
    (r"(?:如果|若|如).{0,30}(?:涉及|包含|含有|传输|出境|处理.*敏感)", "条件性出境/敏感数据"),
    (r"(?:可能|或将|预计|计划).{0,30}(?:涉及|传输|出境|共享|提供)", "可能涉及传输/共享"),
    (r"(?:详见|参见|参考|另行|另见).{0,20}(?:附件|附录|协议)", "引用外部文件"),
    (r"(?:不?确定|未明确|待确认|尚不确定|待定)", "未确认信息"),
]


class ScenarioGraph:
    def __init__(self) -> None:
        self.actors: list[dict] = []
        self.data_flows: list[dict] = []
        self.cross_border_indicators: list[str] = []
        self.legal_grounds: list[str] = []
        self.uncertain_facts: list[str] = []

    def to_dict(self) -> dict:
        return {
            "actors": self.actors,
            "data_flows": self.data_flows,
            "cross_border_indicators": self.cross_border_indicators,
            "legal_grounds": self.legal_grounds,
            "uncertain_facts": self.uncertain_facts,
        }


class ScenarioGraphBuilder:
    """Build structured scenario graphs from document text.

    Strategy: first locate all cross‑border locations, then for each
    location find the nearest action verb, actor, and data items.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def build(self, text: str) -> ScenarioGraph:
        g = ScenarioGraph()
        t = text[:8000]

        # 1. Actors
        seen: set[str] = set()
        for pat, role in _ACTOR_PATTERNS:
            for m in pat.finditer(t):
                name = m.group(1).strip()
                if name not in seen and len(name) >= 3:
                    seen.add(name)
                    g.actors.append({"name": name, "role": role,
                                     "country_or_region": self._country_in(name, t)})

        # 2. Cross‑border data flows — locate all overseas mentions,
        #    then find nearest action + actor for each
        for loc_match in _OVERSEAS_RE.finditer(t):
            loc = loc_match.group(0)
            pos = loc_match.start()
            window = t[max(0, pos-200):min(len(t), pos+200)]

            # Find nearest action
            action = self._nearest_action(window, pos - max(0, pos-200))
            if not action:
                continue

            # Find data items in the window
            items = [kw for kw in _DATA_KEYWORDS if kw in window]

            # Find nearest actor
            source = None
            best = 9999
            for a in g.actors:
                idx = t.find(a["name"])
                if 0 <= idx and abs(idx - pos) < best:
                    best = abs(idx - pos)
                    source = a["name"]

            if source:
                g.data_flows.append({
                    "from_actor": source,
                    "to_actor_or_location": loc,
                    "data_items": items[:5],
                    "action": action,
                    "cross_border": True,
                })

        # 3. Cross‑border indicators
        for pat in _CB_INDICATOR_PATTERNS:
            for m in re.finditer(pat, t, re.IGNORECASE):
                ind = m.group(0)[:100]
                if ind not in g.cross_border_indicators:
                    g.cross_border_indicators.append(ind)

        # 4. Legal grounds
        for pat, label in _LEGAL_GROUND_PATTERNS:
            if pat.search(t):
                g.legal_grounds.append(label)

        # 5. Uncertain facts
        for pat, label in _UNCERTAIN_PATTERNS:
            if re.search(pat, t, re.IGNORECASE):
                g.uncertain_facts.append(label)

        return g

    # -- helpers --

    @staticmethod
    def _country_in(name: str, text: str) -> str:
        for c in _OVERSEAS:
            if c in name:
                return c
        idx = text.find(name)
        if idx >= 0:
            nearby = text[max(0, idx-80):idx+80]
            for c in _OVERSEAS:
                if c in nearby:
                    return c
        if any(c in name for c in ["中国", "北京", "上海", "深圳", "广州", "杭州"]):
            return "中国"
        return "未知"

    @staticmethod
    def _nearest_action(window: str, rel_pos: int) -> str | None:
        best_action = None
        best_dist = 999
        for act in _ACTIONS:
            idx = window.find(act)
            if 0 <= idx:
                dist = abs(idx - rel_pos)
                if dist < best_dist:
                    best_dist = dist
                    best_action = act
        return best_action
