#!/usr/bin/env python3
"""Build a larger, split-aware RAG evaluation dataset with source-level gold labels."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "doc/knowledge/evaluation/rag_eval_v2_queries.csv"

PARAPHRASE_TEMPLATES = (
    "{q}",
    "请给我{q}，并附法规依据。",
    "{q}（需要可追溯的法条来源）",
)


@dataclass(frozen=True)
class BaseQuery:
    text: str
    gold_source_ids: tuple[str, ...]
    difficulty: str


@dataclass(frozen=True)
class ModulePack:
    jurisdiction: str
    path: str
    positives: tuple[BaseQuery, ...]
    negatives: tuple[str, ...]


MODULES: dict[str, ModulePack] = {
    "diagnosis": ModulePack(
        jurisdiction="cn",
        path="all",
        positives=(
            BaseQuery("数据出境怎么先做路径诊断再决定走哪条路线", ("CN-REG-007", "CN-LAW-003"), "medium"),
            BaseQuery("什么情况下应优先走安全评估而不是标准合同", ("CN-REG-004", "CN-REG-007"), "hard"),
            BaseQuery("个人信息出境合规路径的分流规则是什么", ("CN-REG-007", "CN-LAW-003"), "medium"),
            BaseQuery("重要数据和个人信息在出境路径上如何区分", ("CN-LAW-002", "CN-REG-007"), "hard"),
            BaseQuery("触发数据出境合规义务的关键门槛有哪些", ("CN-LAW-003", "CN-REG-006"), "hard"),
            BaseQuery("标准合同和安全评估的适用边界怎么判断", ("CN-REG-005", "CN-REG-004"), "hard"),
            BaseQuery("新规下企业做跨境数据前置自查要看哪些条文", ("CN-REG-007", "CN-REG-008"), "medium"),
            BaseQuery("跨境场景里先判断法定义务再选路径的依据有哪些", ("CN-LAW-003", "CN-REG-007"), "medium"),
        ),
        negatives=(
            "加州CPRA下的消费者删除权是什么",
            "GDPR第47条BCR审批要求有哪些",
            "帮我推荐北京火锅店",
            "美国EO 14117限制交易定义是什么",
            "请解释EDPB 01/2020 Step 3",
            "如何写Python爬虫",
        ),
    ),
    "assessment": ModulePack(
        jurisdiction="cn",
        path="assessment",
        positives=(
            BaseQuery("数据出境安全评估办法里申报触发条件是什么", ("CN-REG-004",), "medium"),
            BaseQuery("安全评估申报材料应如何准备", ("CN-GUIDE-009",), "medium"),
            BaseQuery("评估里如何论证个人信息出境必要性", ("CN-QA-012", "CN-QA-013"), "hard"),
            BaseQuery("重要数据识别在评估环节有哪些口径", ("CN-QA-012", "CN-LAW-002"), "hard"),
            BaseQuery("网信办数据出境安全评估的流程节点有哪些", ("CN-GUIDE-009", "CN-REG-004"), "medium"),
            BaseQuery("个人信息数量规模和敏感信息门槛如何影响评估", ("CN-REG-004", "CN-QA-013"), "hard"),
            BaseQuery("评估报告中高风险事项通常如何写", ("CN-GUIDE-009", "CN-QA-012"), "medium"),
            BaseQuery("安全评估与合规整改闭环怎么做", ("CN-QA-013", "CN-REG-004"), "hard"),
        ),
        negatives=(
            "GDPR DPIA触发条件是什么",
            "CPRA敏感个人信息限制使用怎么做",
            "美国覆盖人员covered person定义是什么",
            "推荐一个好用的IDE",
            "BCR和SCC有什么区别",
            "今天上海天气如何",
        ),
    ),
    "scc": ModulePack(
        jurisdiction="cn",
        path="scc",
        positives=(
            BaseQuery("个人信息出境标准合同办法的核心义务有哪些", ("CN-REG-005", "CN-GOV-015"), "medium"),
            BaseQuery("标准合同备案需要哪些材料", ("CN-QA-011", "CN-GUIDE-010"), "medium"),
            BaseQuery("标准合同生效后多长时间内要备案", ("CN-QA-011", "CN-REG-005"), "hard"),
            BaseQuery("哪些变更情形触发重新评估和重新备案", ("CN-QA-011", "CN-GOV-015"), "hard"),
            BaseQuery("SCC路径下PIPIA评估应覆盖哪些要点", ("CN-QA-011", "CN-REG-005"), "medium"),
            BaseQuery("省级网信备案与联系方式在哪里查", ("CN-OPS-014", "CN-GUIDE-010"), "medium"),
            BaseQuery("标准合同附录和主体条款各自作用是什么", ("CN-QA-011", "CN-REG-005"), "hard"),
            BaseQuery("企业怎么证明标准合同路径的合规完整性", ("CN-GUIDE-010", "CN-REG-005"), "hard"),
        ),
        negatives=(
            "GDPR第35条DPIA要素",
            "美国EO14117 restricted transactions定义",
            "CPRA right to know说明",
            "请写一个冒泡排序",
            "BCR审查要点有哪些",
            "北京地铁几点停运",
        ),
    ),
    "review": ModulePack(
        jurisdiction="cn",
        path="all",
        positives=(
            BaseQuery("合同审查中个人信息处理合法性应依据哪些规则", ("CN-LAW-003",), "medium"),
            BaseQuery("跨境条款审查如何识别超范围收集风险", ("CN-LAW-003", "CN-REG-008"), "hard"),
            BaseQuery("数据处理协议里的安全保障条款如何对标法规", ("CN-REG-008", "CN-LAW-001"), "hard"),
            BaseQuery("合同中个人信息保存期限应如何合规表述", ("CN-LAW-003",), "medium"),
            BaseQuery("审查报告里如何引用中国数据安全法依据", ("CN-LAW-002",), "medium"),
            BaseQuery("发现出境条款缺失时应提示哪些整改建议", ("CN-REG-007", "CN-REG-005"), "hard"),
            BaseQuery("审查时如何区分重要数据和个人信息义务", ("CN-LAW-002", "CN-LAW-003"), "hard"),
            BaseQuery("网络数据安全管理条例可用于哪些合同条款核验", ("CN-REG-008",), "medium"),
        ),
        negatives=(
            "EDPB Step 1内容是什么",
            "美国covered person怎么判定",
            "CPRA删除权时限是多少",
            "推荐一款机械键盘",
            "今天美元汇率",
            "如何做意大利面",
        ),
    ),
    "general": ModulePack(
        jurisdiction="cn",
        path="all",
        positives=(
            BaseQuery("通用法律咨询里如何解释个人信息处理最小必要原则", ("CN-LAW-003",), "medium"),
            BaseQuery("企业出境前做合规备忘录应引用哪些中国法源", ("CN-LAW-003", "CN-LAW-002", "CN-REG-007"), "medium"),
            BaseQuery("如何给管理层解释网络数据安全管理条例的重点", ("CN-REG-008",), "medium"),
            BaseQuery("对外披露个人信息时企业应承担哪些义务", ("CN-LAW-003",), "hard"),
            BaseQuery("通用咨询里常见的数据分类分级依据有哪些", ("CN-LAW-002", "CN-REG-008"), "hard"),
            BaseQuery("跨境场景中中国法下可行路径的高层建议是什么", ("CN-REG-007", "CN-REG-004", "CN-REG-005"), "hard"),
            BaseQuery("合规咨询答复里如何保证可追溯引用", ("CN-LAW-003", "CN-REG-007"), "medium"),
            BaseQuery("中国个人信息保护法与数据安全法如何协同适用", ("CN-LAW-003", "CN-LAW-002"), "hard"),
        ),
        negatives=(
            "GDPR Article 47 BCR requirements",
            "EO 14117 section 202.214 text",
            "CPRA sensitive personal information definition",
            "帮我写一封求职邮件",
            "东京机票多少钱",
            "如何安装nodejs",
        ),
    ),
    "bcr": ModulePack(
        jurisdiction="eu",
        path="all",
        positives=(
            BaseQuery("What does GDPR Article 47 require for BCR approval", ("EU-LAW-001",), "medium"),
            BaseQuery("BCR enforceable rights and liability under GDPR", ("EU-LAW-001",), "hard"),
            BaseQuery("How should BCR describe onward transfer safeguards", ("EU-LAW-001", "EU-GUIDE-002"), "hard"),
            BaseQuery("BCR review checklist for supervisory authority expectations", ("EU-LAW-001",), "medium"),
            BaseQuery("Cross-border intra-group transfer governance under Article 47", ("EU-LAW-001",), "medium"),
            BaseQuery("How EDPB transfer methodology supports BCR operational controls", ("EU-GUIDE-002", "EU-LAW-001"), "hard"),
            BaseQuery("Key mandatory elements in BCR documentation", ("EU-LAW-001",), "medium"),
            BaseQuery("BCR compliance review for complaint handling and redress", ("EU-LAW-001",), "hard"),
        ),
        negatives=(
            "中国标准合同备案需要什么材料",
            "CPRA right to know details",
            "EO 14117 restricted transactions",
            "recipe for chocolate cake",
            "python list comprehension tutorial",
            "北京住房公积金比例",
        ),
    ),
    "dpia": ModulePack(
        jurisdiction="eu",
        path="all",
        positives=(
            BaseQuery("When is a DPIA required under GDPR Article 35", ("EU-LAW-001",), "medium"),
            BaseQuery("DPIA must-cover elements: necessity proportionality risk measures", ("EU-LAW-001",), "hard"),
            BaseQuery("How to map transfers before DPIA for cross-border processing", ("EU-GUIDE-002", "EU-LAW-001"), "hard"),
            BaseQuery("High-risk processing indicators for DPIA trigger", ("EU-LAW-001",), "medium"),
            BaseQuery("DPIA workflow and documentation evidence", ("EU-LAW-001", "EU-GUIDE-002"), "medium"),
            BaseQuery("Supervisory consultation after DPIA high risk finding", ("EU-LAW-001",), "hard"),
            BaseQuery("DPIA and transfer impact assessment relation in practice", ("EU-GUIDE-002", "EU-LAW-001"), "hard"),
            BaseQuery("Article 35 checklist for legal team", ("EU-LAW-001",), "medium"),
        ),
        negatives=(
            "中国数据出境安全评估申报指南",
            "CPRA sensitive personal information",
            "EO 14117 covered person definition",
            "how to tune mysql",
            "best laptop under 1000",
            "深圳地铁线路图",
        ),
    ),
    "tia": ModulePack(
        jurisdiction="eu",
        path="all",
        positives=(
            BaseQuery("EDPB Recommendations 01/2020 Step 1 transfer mapping requirements", ("EU-GUIDE-002",), "medium"),
            BaseQuery("TIA Step 3 third-country law assessment approach", ("EU-GUIDE-002",), "hard"),
            BaseQuery("How to determine if Article 46 transfer tool is effective", ("EU-GUIDE-002",), "hard"),
            BaseQuery("Supplementary measures in Schrems II context", ("EU-GUIDE-002",), "medium"),
            BaseQuery("Transfer impact assessment evidence package", ("EU-GUIDE-002", "EU-LAW-001"), "medium"),
            BaseQuery("How to re-evaluate transfer risk over time", ("EU-GUIDE-002",), "hard"),
            BaseQuery("SCC/BCR tool selection before TIA", ("EU-GUIDE-002", "EU-LAW-001"), "hard"),
            BaseQuery("What legal benchmarks are used in TIA proportionality analysis", ("EU-GUIDE-002",), "hard"),
        ),
        negatives=(
            "中国标准合同办法第七条是什么",
            "美国CPRA right to limit",
            "EO 14117 Sec. 202.214 meaning",
            "how to use docker compose",
            "法国旅游攻略",
            "高考志愿填报建议",
        ),
    ),
    "cn_flow": ModulePack(
        jurisdiction="us",
        path="all",
        positives=(
            BaseQuery("EO 14117 final rule summary for restricted transactions", ("US-FED-001",), "medium"),
            BaseQuery("What is a covered person under 28 CFR 202.211", ("US-FED-001",), "medium"),
            BaseQuery("How data brokerage is defined under 28 CFR 202.214", ("US-FED-001",), "medium"),
            BaseQuery("U.S. sensitive personal data export risk controls to countries of concern", ("US-FED-001",), "hard"),
            BaseQuery("Compliance obligations for prohibited vs restricted transactions", ("US-FED-001",), "hard"),
            BaseQuery("Cross-border data deal screening under DOJ EO 14117 rule", ("US-FED-001",), "medium"),
            BaseQuery("Who can be designated as covered person and why it matters", ("US-FED-001",), "hard"),
            BaseQuery("Operational checklist for U.S.-China flow restrictions", ("US-FED-001",), "hard"),
        ),
        negatives=(
            "GDPR Article 35 DPIA requirements",
            "CPRA right to know details",
            "中国数据出境安全评估办法",
            "how to configure nginx",
            "日本签证办理流程",
            "双色球号码推荐",
        ),
    ),
    "cpra": ModulePack(
        jurisdiction="us",
        path="all",
        positives=(
            BaseQuery("What is the CPRA right to know", ("US-CA-001",), "medium"),
            BaseQuery("Right to limit use and disclosure of sensitive personal information", ("US-CA-001",), "medium"),
            BaseQuery("How CPRA defines sensitive personal information", ("US-CA-001",), "hard"),
            BaseQuery("Consumer deletion/correction rights under California privacy rules", ("US-CA-001",), "hard"),
            BaseQuery("What notices should a business provide under CCPA/CPRA", ("US-CA-001",), "medium"),
            BaseQuery("CPRA compliance points for handling consumer requests", ("US-CA-001",), "medium"),
            BaseQuery("Difference between right to opt-out and right to limit in CPRA", ("US-CA-001",), "hard"),
            BaseQuery("How to explain CPRA consumer rights framework to product teams", ("US-CA-001",), "hard"),
        ),
        negatives=(
            "EO 14117 covered person definition",
            "GDPR Article 47 BCR",
            "中国个人信息保护法跨境规则",
            "how to cook steak",
            "macbook battery cycle count",
            "杭州周末去哪玩",
        ),
    ),
}


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    qidx = 1
    for module, pack in MODULES.items():
        # 24 positives: 8 base queries x 3 paraphrases
        for base in pack.positives:
            for template in PARAPHRASE_TEMPLATES:
                query = template.format(q=base.text)
                split = "holdout" if qidx % 5 == 0 else "train"
                rows.append(
                    {
                        "query_id": f"Q{qidx:04d}",
                        "module": module,
                        "split": split,
                        "difficulty": base.difficulty,
                        "label_type": "positive",
                        "query": query,
                        "gold_source_ids": "|".join(base.gold_source_ids),
                        "gold_article_ids": "",
                        "expected_jurisdiction": pack.jurisdiction,
                        "expected_path": pack.path,
                        "expected_empty": "no",
                        "notes": "paraphrased-positive",
                    }
                )
                qidx += 1

        # 6 negatives per module => total 30/module
        for neg in pack.negatives:
            split = "holdout" if qidx % 5 == 0 else "train"
            rows.append(
                {
                    "query_id": f"Q{qidx:04d}",
                    "module": module,
                    "split": split,
                    "difficulty": "hard",
                    "label_type": "negative",
                    "query": neg,
                    "gold_source_ids": "",
                    "gold_article_ids": "",
                    "expected_jurisdiction": pack.jurisdiction,
                    "expected_path": pack.path,
                    "expected_empty": "yes",
                    "notes": "hard-negative-out-of-domain",
                }
            )
            qidx += 1

    return rows


def main() -> None:
    rows = build_rows()
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "query_id",
                "module",
                "split",
                "difficulty",
                "label_type",
                "query",
                "gold_source_ids",
                "gold_article_ids",
                "expected_jurisdiction",
                "expected_path",
                "expected_empty",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote: {OUT_CSV}")
    print(f"rows: {len(rows)}")


if __name__ == "__main__":
    main()
