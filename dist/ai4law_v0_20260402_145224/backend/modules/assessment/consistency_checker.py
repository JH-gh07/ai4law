from backend.modules.assessment.schema import ChapterContent, CompanyProfile


class ConsistencyChecker:
    def check(self, profile: CompanyProfile, chapters: list[ChapterContent]) -> list[str]:
        issues: list[str] = []
        if not chapters:
            return ["No chapters generated."]

        for chapter in chapters:
            if not chapter.citations:
                issues.append(f"Chapter {chapter.chapter_no} has no citation.")

        high_risk = profile.is_ciio or profile.contains_important_data or profile.pii_count >= 1_000_000
        if high_risk and chapters[-1].risk_level != "HIGH":
            issues.append("Final chapter risk level should be HIGH under mandatory security-assessment conditions.")

        return issues
