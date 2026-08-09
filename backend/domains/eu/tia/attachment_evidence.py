"""TIA attachment evidence extractor."""

from __future__ import annotations

import re

from backend.common.storage.file_parser import FileParser
from backend.domains.eu.tia.schema import TIAAttachment


class TIAAttachmentEvidence:
    def __init__(self, parser: FileParser | None = None) -> None:
        self.parser = parser or FileParser()

    def extract(self, attachment: TIAAttachment, *, text: str | None = None) -> dict:
        if text is None:
            try:
                text = self.parser.parse_text(attachment.storage_uri)
            except Exception:
                return {"role": attachment.file_role, "parse_error": True}

        t = text.lower()

        if attachment.file_role == "transfer_agreement":
            return self._extract_transfer_agreement(t)
        elif attachment.file_role == "country_law_analysis":
            return self._extract_country_law(t)
        elif attachment.file_role == "technical_control_doc":
            return self._extract_technical_controls(t)
        return {"role": attachment.file_role, "text_length": len(text)}

    def _extract_transfer_agreement(self, t: str) -> dict:
        return {
            "role": "transfer_agreement",
            "has_scc_mention": bool(re.search(r"scc|standard contractual clause|标准合同条款", t, re.IGNORECASE)),
            "is_2021_914_scc": bool(re.search(r"2021/914|2021.*scc|scc.*2021", t, re.IGNORECASE)),
            "has_module_selection": bool(re.search(r"module\s*(one|two|three|four|1|2|3|4)", t, re.IGNORECASE)),
            "has_bcr_mention": bool(re.search(r"binding corporate rules|\bBCRs?\b|约束性公司规则", t, re.IGNORECASE)),
            "has_article_49_derogation": bool(re.search(r"article\s*49|derogation|第\s*49\s*条|例外情形", t, re.IGNORECASE)),
            "has_gov_access_notice": bool(re.search(r"government.*access|government.*request|执法.*请求|政府.*访问", t, re.IGNORECASE)),
            "has_onward_transfer_restriction": bool(re.search(r"onward.*transfer|sub.?processor|再传输", t, re.IGNORECASE)),
            "has_audit_rights": bool(re.search(r"audit|inspection|审计|检查", t, re.IGNORECASE)),
        }

    def _extract_country_law(self, t: str) -> dict:
        countries: list[str] = []
        for c in ["United States", "India", "China", "United Kingdom", "Singapore",
                    "Japan", "South Korea", "Australia", "Brazil"]:
            if c.lower() in t:
                countries.append(c)
        return {
            "role": "country_law_analysis",
            "countries_mentioned": countries,
            "has_gov_access_analysis": bool(re.search(r"government.*access|surveillance|监控|FISA|national security|执法", t, re.IGNORECASE)),
            "has_remedy_assessment": bool(re.search(r"remedy|redress|救济|complaint|司法", t, re.IGNORECASE)),
            "has_oversight_assessment": bool(re.search(r"oversight|independent|supervisory|独立|监管", t, re.IGNORECASE)),
            "has_edpb_reference": bool(re.search(r"edpb|schrems|european data protection board", t, re.IGNORECASE)),
        }

    def _extract_technical_controls(self, t: str) -> dict:
        return {
            "role": "technical_control_doc",
            "has_encryption_at_rest": bool(re.search(r"encryption.*rest|encryption.*storage|静态加密|存储加密", t, re.IGNORECASE)),
            "has_encryption_in_transit": bool(re.search(r"encryption.*transit|encryption.*transport|传输加密|TLS|HTTPS", t, re.IGNORECASE)),
            "has_end_to_end_encryption": bool(re.search(r"end.?to.?end.*encrypt|e2ee|端到端加密", t, re.IGNORECASE)),
            "has_key_management": bool(re.search(r"key.*manage|key.*control|密钥管理|key.*rotation", t, re.IGNORECASE)),
            "key_location_eu": bool(re.search(
                r"(?:key.*(?:EU|Europe|Germany|France|Ireland|Netherlands)|"
                r"(?:EU|Europe|Germany|France|Ireland|Netherlands).*key)",
                t,
                re.IGNORECASE,
            )),
            "has_secure_enclave": bool(re.search(r"secure enclave|安全飞地|trusted execution|confidential computing|机密计算", t, re.IGNORECASE)),
            "has_key_separation": bool(re.search(r"key.*separat|separate.*key|密钥分离|密钥隔离", t, re.IGNORECASE)),
            "has_audit_logging": bool(re.search(r"audit.*log|审计.*日志|access.*log", t, re.IGNORECASE)),
            "has_access_control": bool(re.search(r"access.*control|访问控制|RBAC|role.?based|MFA|2FA", t, re.IGNORECASE)),
        }
