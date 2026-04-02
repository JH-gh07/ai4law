from backend.schemas.review import RevisedClause, SectionType


class DocumentRecomposer:
    def build_sections(self, clauses: list[RevisedClause]) -> list[tuple[str, list[str]]]:
        body_lines: list[str] = []
        appendix_lines: list[str] = []
        diff_note_lines: list[str] = []

        for clause in clauses:
            entry = clause.revised_text
            if clause.heading and not entry.startswith(clause.heading):
                entry = f"{clause.heading}\n{entry}"
            if clause.section_type == SectionType.APPENDIX:
                appendix_lines.append(entry)
            else:
                body_lines.append(entry)
            diff_note_lines.append(f"{clause.heading or clause.clause_id}：{clause.revision_reason}")

        sections = [("修订后合同正文", body_lines or ["无正文内容。"])]
        if appendix_lines:
            sections.append(("修订后附录", appendix_lines))
        sections.append(("修订说明", diff_note_lines))
        return sections
