import re
from uuid import uuid4

from backend.schemas.review import Clause, ClausePosition, SectionType


class ClauseSegmenter:
    heading_pattern = re.compile(
        r"^(第[一二三四五六七八九十百千万0-9]+条|[0-9]+[\.、]|[一二三四五六七八九十]+、|附件[一二三四五六七八九十0-9]*|附录[一二三四五六七八九十0-9]*)"
    )
    appendix_pattern = re.compile(r"^(附件|附录)([一二三四五六七八九十0-9]*)")

    def segment(self, file_id: str, text: str) -> list[Clause]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.strip() for line in normalized.split("\n") if line.strip()]
        if not lines:
            return []

        clauses: list[Clause] = []
        buffer: list[str] = []
        current_heading: str | None = None
        current_section = SectionType.BODY
        current_appendix_id: str | None = None
        paragraph = 0

        def flush() -> None:
            nonlocal buffer, current_heading, paragraph
            if not buffer:
                return
            paragraph += 1
            heading = current_heading or buffer[0][:80]
            clause_number = heading.split(" ", 1)[0] if heading else None
            clauses.append(
                Clause(
                    clause_id=str(uuid4()),
                    file_id=file_id,
                    text="\n".join(buffer),
                    heading=heading,
                    section_type=current_section,
                    appendix_id=current_appendix_id,
                    position=ClausePosition(
                        page=1,
                        paragraph=paragraph,
                        clause_number=clause_number,
                        section_path=f"{current_section.value}:{heading}" if heading else current_section.value,
                    ),
                )
            )
            buffer = []

        for line in lines:
            appendix_match = self.appendix_pattern.match(line)
            if appendix_match:
                flush()
                current_section = SectionType.APPENDIX
                current_appendix_id = appendix_match.group(0)
                current_heading = line
                buffer = [line]
                continue

            if self.heading_pattern.match(line) and buffer:
                flush()
                current_heading = line
                if current_section != SectionType.APPENDIX:
                    current_section = SectionType.BODY
                    current_appendix_id = None
                buffer = [line]
                continue

            if not buffer:
                current_heading = line
            buffer.append(line)

        flush()
        return clauses
