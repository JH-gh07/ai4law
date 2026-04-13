from __future__ import annotations

import copy
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

NS = {
    "w": W_NS,
    "r": R_NS,
    "ct": CONTENT_TYPES_NS,
    "pr": REL_NS,
}

COMMENTS_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
COMMENTS_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"

EXTRA_NAMESPACES = {
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "o": "urn:schemas-microsoft-com:office:office",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "v": "urn:schemas-microsoft-com:vml",
    "wp14": "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "w10": "urn:schemas-microsoft-com:office:word",
    "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
    "wpc": "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas",
    "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
    "wpi": "http://schemas.microsoft.com/office/word/2010/wordprocessingInk",
    "wne": "http://schemas.microsoft.com/office/word/2006/wordml",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "wpsCustomData": "http://www.wps.cn/officeDocument/2013/wpsCustomData",
}

STOPWORDS = {
    "合同",
    "条款",
    "问题",
    "建议",
    "风险",
    "依据",
    "标准",
    "审查",
    "要求",
    "说明",
    "内容",
    "相关",
    "进行",
    "增加",
    "应当",
    "需要",
    "complete",
    "draft",
    "review",
    "report",
}


for prefix, uri in {"w": W_NS, "r": R_NS, "ct": CONTENT_TYPES_NS, "pr": REL_NS, **EXTRA_NAMESPACES}.items():
    ET.register_namespace(prefix, uri)


@dataclass(slots=True)
class DocxComment:
    label: str
    basis: str
    risk_level: str
    risk_analysis: str
    suggestion: str
    location: str = ""
    quote: str = ""


@dataclass(slots=True)
class ParagraphTarget:
    paragraph: ET.Element
    text: str
    score: int


def render_commented_docx(
    source_path: Path,
    output_path: Path,
    comments: Iterable[DocxComment],
    author: str = "AI4Law",
    initials: str = "AR",
) -> Path | None:
    if source_path.suffix.lower() != ".docx" or not source_path.exists():
        return None

    comment_list = [item for item in comments if _has_payload(item)]
    if not comment_list:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source_path, "r") as source_zip:
        files = {entry.filename: source_zip.read(entry.filename) for entry in source_zip.infolist()}

    if "word/document.xml" not in files:
        return None

    document_tree = ET.ElementTree(ET.fromstring(files["word/document.xml"]))
    comments_tree = _load_comments_tree(files.get("word/comments.xml"))
    content_types_tree = ET.ElementTree(ET.fromstring(files["[Content_Types].xml"]))
    rels_tree = ET.ElementTree(ET.fromstring(files["word/_rels/document.xml.rels"]))

    comments_root = comments_tree.getroot()
    next_comment_id = _next_comment_id(comments_root)
    paragraphs = _collect_paragraphs(document_tree.getroot())
    used_paragraph_ids: set[int] = set()

    for item in comment_list:
        target = _match_paragraph(item, paragraphs, used_paragraph_ids)
        if target is None:
            continue
        used_paragraph_ids.add(id(target.paragraph))
        _insert_comment_anchor(target.paragraph, next_comment_id)
        comments_root.append(_build_comment_node(next_comment_id, item, author=author, initials=initials))
        next_comment_id += 1

    _ensure_content_type(content_types_tree.getroot())
    _ensure_comments_relationship(rels_tree.getroot())

    files["word/document.xml"] = _serialize_xml(document_tree.getroot())
    files["word/comments.xml"] = _serialize_xml(comments_root)
    files["[Content_Types].xml"] = _serialize_xml(content_types_tree.getroot())
    files["word/_rels/document.xml.rels"] = _serialize_xml(rels_tree.getroot())

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as output_zip:
        for filename, payload in files.items():
            output_zip.writestr(filename, payload)

    return output_path


def _has_payload(item: DocxComment) -> bool:
    return any(
        value.strip()
        for value in [item.label, item.basis, item.risk_level, item.risk_analysis, item.suggestion, item.location, item.quote]
    )


def _load_comments_tree(raw_xml: bytes | None) -> ET.ElementTree:
    if raw_xml:
        return ET.ElementTree(ET.fromstring(raw_xml))
    root = ET.Element(f"{{{W_NS}}}comments")
    return ET.ElementTree(root)


def _next_comment_id(root: ET.Element) -> int:
    ids = []
    for node in root.findall("w:comment", NS):
        raw_id = node.get(f"{{{W_NS}}}id")
        if raw_id and raw_id.isdigit():
            ids.append(int(raw_id))
    return max(ids, default=0) + 1


def _collect_paragraphs(root: ET.Element) -> list[ParagraphTarget]:
    targets: list[ParagraphTarget] = []
    for paragraph in root.findall(".//w:p", NS):
        text = _paragraph_text(paragraph)
        if not text.strip():
            continue
        targets.append(ParagraphTarget(paragraph=paragraph, text=text.strip(), score=0))
    return targets


def _paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.findall(".//w:t", NS))


def _match_paragraph(
    item: DocxComment,
    paragraphs: list[ParagraphTarget],
    used_paragraph_ids: set[int],
) -> ParagraphTarget | None:
    best: ParagraphTarget | None = None
    best_score = -1
    keywords = _keywords_for_comment(item)

    for target in paragraphs:
        if id(target.paragraph) in used_paragraph_ids:
            continue
        score = _score_paragraph(target.text, item, keywords)
        if score > best_score:
            best = target
            best_score = score

    if best and best_score > 0:
        return best

    for target in paragraphs:
        if id(target.paragraph) in used_paragraph_ids:
            continue
        return target
    return None


def _keywords_for_comment(item: DocxComment) -> list[str]:
    raw = " ".join([item.label, item.location, item.quote, item.basis, item.risk_analysis])
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}|\d{2,}", raw)
    seen: set[str] = set()
    result: list[str] = []
    for token in tokens:
        lowered = token.lower()
        if lowered in STOPWORDS:
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(token)
    return result[:10]


def _score_paragraph(text: str, item: DocxComment, keywords: list[str]) -> int:
    score = 0
    compact = re.sub(r"\s+", "", text)
    quote = re.sub(r"\s+", "", item.quote)

    if quote and len(quote) >= 4 and quote in compact:
        score += 100
    for keyword in keywords:
        if keyword and keyword in text:
            score += min(len(keyword), 12)

    location = item.location.strip()
    if location and location in text:
        score += 40

    if not score and item.label and item.label in text:
        score += 20
    return score


def _insert_comment_anchor(paragraph: ET.Element, comment_id: int) -> None:
    first_run_idx = None
    last_run_idx = None
    children = list(paragraph)
    for idx, child in enumerate(children):
        if child.tag == f"{{{W_NS}}}r":
            if first_run_idx is None:
                first_run_idx = idx
            last_run_idx = idx

    if first_run_idx is None or last_run_idx is None:
        return

    start = ET.Element(f"{{{W_NS}}}commentRangeStart", {f"{{{W_NS}}}id": str(comment_id)})
    end = ET.Element(f"{{{W_NS}}}commentRangeEnd", {f"{{{W_NS}}}id": str(comment_id)})
    ref_run = ET.Element(f"{{{W_NS}}}r")
    ref = ET.SubElement(ref_run, f"{{{W_NS}}}commentReference", {f"{{{W_NS}}}id": str(comment_id)})
    ref.tail = None

    paragraph.insert(first_run_idx, start)
    paragraph.insert(last_run_idx + 2, end)
    paragraph.insert(last_run_idx + 3, ref_run)


def _build_comment_node(comment_id: int, item: DocxComment, author: str, initials: str) -> ET.Element:
    comment = ET.Element(
        f"{{{W_NS}}}comment",
        {
            f"{{{W_NS}}}id": str(comment_id),
            f"{{{W_NS}}}author": author,
            f"{{{W_NS}}}initials": initials,
        },
    )

    lines = [
        "风险点名称",
        item.label,
        "定位",
        item.location or "全文匹配",
        "风险等级",
        item.risk_level,
        "审核规则",
        item.basis,
        "风险分析",
        item.risk_analysis,
        "建议",
        item.suggestion,
    ]
    if item.quote:
        lines.extend(["原文摘录", item.quote])

    for line in lines:
        if not line:
            continue
        paragraph = ET.SubElement(comment, f"{{{W_NS}}}p")
        run = ET.SubElement(paragraph, f"{{{W_NS}}}r")
        text = ET.SubElement(run, f"{{{W_NS}}}t")
        text.text = line
    return comment


def _ensure_content_type(root: ET.Element) -> None:
    for node in root.findall("ct:Override", NS):
        if node.get("PartName") == "/word/comments.xml":
            return
    ET.SubElement(
        root,
        f"{{{CONTENT_TYPES_NS}}}Override",
        {
            "PartName": "/word/comments.xml",
            "ContentType": COMMENTS_CONTENT_TYPE,
        },
    )


def _ensure_comments_relationship(root: ET.Element) -> None:
    for node in root.findall("pr:Relationship", NS):
        if node.get("Type") == COMMENTS_REL_TYPE:
            return

    existing_ids: set[int] = set()
    for node in root.findall("pr:Relationship", NS):
        rel_id = node.get("Id", "")
        match = re.fullmatch(r"rId(\d+)", rel_id)
        if match:
            existing_ids.add(int(match.group(1)))
    next_id = max(existing_ids, default=0) + 1

    ET.SubElement(
        root,
        f"{{{REL_NS}}}Relationship",
        {
            "Id": f"rId{next_id}",
            "Type": COMMENTS_REL_TYPE,
            "Target": "comments.xml",
        },
    )


def _serialize_xml(root: ET.Element) -> bytes:
    cloned = copy.deepcopy(root)
    return ET.tostring(cloned, encoding="utf-8", xml_declaration=True)
