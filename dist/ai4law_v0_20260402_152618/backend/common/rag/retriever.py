from dataclasses import dataclass


@dataclass
class RegulationDoc:
    id: str
    title: str
    article: str
    content: str


REGULATION_DB = [
    RegulationDoc(
        id="pipl-40",
        title="个人信息保护法",
        article="第40条",
        content="关键信息基础设施运营者和处理个人信息达到国家网信部门规定数量的处理者，应当通过国家网信部门组织的安全评估。",
    ),
    RegulationDoc(
        id="dsl-21",
        title="数据安全法",
        article="第21条",
        content="国家建立数据分类分级保护制度，对重要数据实行重点保护。",
    ),
    RegulationDoc(
        id="scc-measures-7",
        title="个人信息出境标准合同办法",
        article="第7条",
        content="个人信息处理者向境外提供个人信息前，应开展个人信息保护影响评估。",
    ),
    RegulationDoc(
        id="security-assessment-measures-4",
        title="数据出境安全评估办法",
        article="第4条",
        content="数据处理者向境外提供重要数据或者达到个人信息数量门槛的，应当申报数据出境安全评估。",
    ),
    RegulationDoc(
        id="gbt-46068",
        title="GB/T 46068-2025",
        article="通则",
        content="规定个人信息跨境处理活动的认证框架与要求。",
    ),
]


def retrieve_regulations(query: str, top_k: int = 8) -> list[RegulationDoc]:
    keywords = {token.strip().lower() for token in query.split() if token.strip()}
    scored: list[tuple[int, RegulationDoc]] = []
    for doc in REGULATION_DB:
        corpus = f"{doc.title} {doc.article} {doc.content}".lower()
        score = sum(1 for kw in keywords if kw in corpus)
        if score > 0:
            scored.append((score, doc))

    if not scored:
        return REGULATION_DB[:top_k]

    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:top_k]]
