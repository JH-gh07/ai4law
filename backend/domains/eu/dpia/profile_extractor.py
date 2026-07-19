"""DPIA profile extractor — builds DPIAProjectProfile from request + attachments."""

from __future__ import annotations

from backend.common.storage.file_parser import FileParser
from backend.domains.cn.security_assessment.attachment_parser import parse_attachment_metadata
from backend.domains.eu.dpia.schema import DPIAProjectProfile, DPIARequest


class DPIAProfileExtractor:
    """Extract a processing-activity profile from a DPIARequest."""

    def __init__(self) -> None:
        self.parser = FileParser()

    def extract(self, payload: DPIARequest) -> DPIAProjectProfile:
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
                if atype != "other" and "missing_summary" in meta:
                    note += f" | {meta['missing_summary']}"

                notes.append(note)
                attachment_metadata.append(meta)
            except (FileNotFoundError, ValueError) as exc:
                notes.append(f"{file_path}: [parse skipped] {exc}")

        return DPIAProjectProfile(
            project_name=payload.project_name,
            project_goal=payload.project_goal,
            processing_flow_description=payload.processing_flow_description,
            data_categories=payload.data_categories,
            special_category_data=payload.special_category_data,
            special_category_types=payload.special_category_types,
            data_subject_categories=payload.data_subject_categories,
            data_subject_count=payload.data_subject_count,
            retention_period=payload.retention_period,
            cross_border_transfer=payload.cross_border_transfer,
            transfer_destination=payload.transfer_destination,
            automated_decision_making=payload.automated_decision_making,
            systematic_monitoring=payload.systematic_monitoring,
            large_scale_processing=payload.large_scale_processing,
            data_matching=payload.data_matching,
            new_technology=payload.new_technology,
            vulnerable_data_subjects=payload.vulnerable_data_subjects,
            lawful_basis=payload.lawful_basis,
            dpia_trigger_reasons=payload.dpia_trigger_reasons,
            dpo_name=payload.dpo_name,
            dpo_opinion=payload.dpo_opinion,
            extracted_notes=notes,
            attachment_metadata=attachment_metadata,
        )
