#!/usr/bin/env python3
"""Build additional hard-negative set for RAG monthly regression."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "doc/knowledge/evaluation/rag_eval_v2_hard_negatives.csv"

FIELDNAMES = [
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
]


def _module_pack() -> dict[str, dict[str, object]]:
    return {
        "diagnosis": {
            "jurisdiction": "cn",
            "path": "all",
            "queries": [
                "GDPR Article 5 principles summary",
                "CPRA right to limit details",
                "EO 14117 covered person definition",
                "帮我写一个爬虫脚本",
                "推荐北京川菜馆",
                "How to configure nginx reverse proxy",
                "BCR approval checklist in EU",
                "EDPB Recommendations 01/2020 Step 3",
            ],
        },
        "assessment": {
            "jurisdiction": "cn",
            "path": "assessment",
            "queries": [
                "GDPR DPIA trigger threshold",
                "CPRA sensitive personal information examples",
                "What is a restricted transaction under EO 14117",
                "how to tune mysql performance",
                "Python list vs tuple",
                "BCR legal basis under GDPR",
                "California deletion right deadline",
                "请推荐一台轻薄本",
            ],
        },
        "scc": {
            "jurisdiction": "cn",
            "path": "scc",
            "queries": [
                "GDPR Article 47 BCR mandatory items",
                "CPRA opt-out right explanation",
                "EO 14117 section 202.214",
                "How to cook steak medium rare",
                "Docker compose healthcheck examples",
                "DPIA template under GDPR",
                "EDPB Step 2 transfer tool review",
                "法国旅游攻略",
            ],
        },
        "review": {
            "jurisdiction": "cn",
            "path": "all",
            "queries": [
                "GDPR Article 35 full text",
                "CPRA right to know request format",
                "EO 14117 countries of concern list",
                "How to use pandas merge",
                "给我一份健身计划",
                "BCR complaint handling under GDPR",
                "EDPB transfer mapping checklist",
                "今日天气预报",
            ],
        },
        "general": {
            "jurisdiction": "cn",
            "path": "all",
            "queries": [
                "GDPR Recital 49 meaning",
                "CPRA purpose limitation rule",
                "EO 14117 compliance deadline",
                "How to install nodejs on mac",
                "推荐上海日料店",
                "BCR binding effect details",
                "Article 35 DPIA necessity test",
                "Best IDE for Java",
            ],
        },
        "bcr": {
            "jurisdiction": "eu",
            "path": "all",
            "queries": [
                "中国标准合同备案材料清单",
                "中国数据出境安全评估触发条件",
                "CPRA right to delete details",
                "EO 14117 covered person Chinese summary",
                "双色球号码推荐",
                "如何配置docker网络",
                "中国个人信息保护法第五十五条内容",
                "今晚吃什么",
            ],
        },
        "dpia": {
            "jurisdiction": "eu",
            "path": "all",
            "queries": [
                "中国网信办安全评估申报指南",
                "中国标准合同办法第七条",
                "CPRA do-not-sell obligations",
                "EO 14117 restricted transaction examples",
                "How to optimize redis",
                "如何学习前端开发",
                "中国个人信息出境路径怎么选",
                "杭州周末去哪玩",
            ],
        },
        "tia": {
            "jurisdiction": "eu",
            "path": "all",
            "queries": [
                "中国数据安全法重点条款",
                "中国网络数据安全管理条例摘要",
                "CPRA sensitive personal information use limits",
                "EO 14117 section 202.211",
                "How to use kubectl port-forward",
                "Macbook battery cycle check",
                "中国标准合同备案时限",
                "推荐一款机械键盘",
            ],
        },
        "cn_flow": {
            "jurisdiction": "us",
            "path": "all",
            "queries": [
                "GDPR Article 46 transfer tools",
                "EDPB Recommendations supplementary measures",
                "中国标准合同办法第十条",
                "中国安全评估办法段落6",
                "How to tune nginx worker_processes",
                "请帮我写个PPT大纲",
                "BCR approval authority in EU",
                "最近好看的电影推荐",
            ],
        },
        "cpra": {
            "jurisdiction": "us",
            "path": "all",
            "queries": [
                "GDPR Article 47 BCR requirements",
                "EDPB 01/2020 Step 4 guidance",
                "中国个人信息保护法跨境条款",
                "中国数据出境安全评估",
                "How to cook pasta al dente",
                "How to configure zsh aliases",
                "DPIA workflow under GDPR",
                "双色球历史号码",
            ],
        },
    }


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    qidx = 1
    for module, cfg in _module_pack().items():
        for query in cfg["queries"]:  # type: ignore[index]
            split = "holdout" if qidx % 4 == 0 else "train"
            rows.append(
                {
                    "query_id": f"HN{qidx:04d}",
                    "module": module,
                    "split": split,
                    "difficulty": "hard",
                    "label_type": "negative",
                    "query": query,
                    "gold_source_ids": "",
                    "gold_article_ids": "",
                    "expected_jurisdiction": str(cfg["jurisdiction"]),
                    "expected_path": str(cfg["path"]),
                    "expected_empty": "yes",
                    "notes": "hard-negative-regression-pack-v1",
                }
            )
            qidx += 1
    return rows


def main() -> None:
    rows = build_rows()
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote: {OUT_CSV}")
    print(f"rows: {len(rows)}")


if __name__ == "__main__":
    main()
