import re
from uuid import uuid4

from backend.schemas.review import Clause, ClausePosition


class ClauseSegmenter:
    split_pattern = re.compile(r"(?=(?:第[一二三四五六七八九十百千万0-9]+条|[0-9]+[\.、]|[一二三四五六七八九十]+、))")

    def segment(self, file_id: str, text: str) -> list[Clause]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        parts = [part.strip() for part in self.split_pattern.split(normalized) if part.strip()]
        if not parts:
            parts = [normalized]

        clauses: list[Clause] = []
        for index, part in enumerate(parts, start=1):
            lines = [line.strip() for line in part.split("\n") if line.strip()]
            heading = lines[0][:80] if lines else None
            clause_number_match = re.match(r"^(第[^\s]+条|[0-9]+[\.、]|[一二三四五六七八九十]+、)", lines[0]) if lines else None
            clauses.append(
                Clause(
                    clause_id=str(uuid4()),
                    file_id=file_id,
                    text=part,
                    heading=heading,
                    position=ClausePosition(page=1, paragraph=index, clause_number=clause_number_match.group(1) if clause_number_match else None),
                )
            )
        return clauses
