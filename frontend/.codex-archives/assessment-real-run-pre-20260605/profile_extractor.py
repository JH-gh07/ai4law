from backend.common.storage.file_parser import FileParser
from backend.modules.assessment.attachment_parser import parse_attachment_metadata
from backend.modules.assessment.schema import AssessmentRequest, CompanyProfile


class ProfileExtractor:
    def __init__(self) -> None:
        self.parser = FileParser()

    def extract(self, payload: AssessmentRequest) -> CompanyProfile:
        notes: list[str] = []
        attachment_metadata: list[dict] = []
        for file_path in payload.uploaded_files:
            try:
                content = self.parser.parse_text(file_path)
                preview = content[:160].replace("\n", " ")
                note = f"{file_path}: {preview}"

                meta = parse_attachment_metadata(file_path, content)
                atype = meta.get("type", "other")
                note += f" [type={atype}]"
                if atype == "contract" and "missing_summary" in meta:
                    note += f" | {meta['missing_summary']}"

                notes.append(note)
                attachment_metadata.append(meta)
            except (FileNotFoundError, ValueError) as exc:
                notes.append(f"{file_path}: [parse skipped] {exc}")

        return CompanyProfile(
            company_name=payload.company_name,
            industry=payload.industry,
            is_ciio=payload.is_ciio,
            contains_important_data=payload.contains_important_data,
            pii_count=payload.pii_count,
            spi_count=payload.spi_count,
            transfer_purpose=payload.transfer_purpose,
            receiver_country=payload.receiver_country,
            extracted_notes=notes,
            attachment_metadata=attachment_metadata,
        )
