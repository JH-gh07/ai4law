"""CPRAAttachmentExtractor — extract compliance facts from CPRA attachments."""

from __future__ import annotations

import re
from typing import Any

from backend.common.storage.file_parser import FileParser
from backend.modules.cpra.schema import CPRAAttachment


class CPRAAttachmentExtractor:
    _OPT_OUT_PATTERNS = [
        r"do\s+not\s+sell\s+or\s+share", r"请勿出售或分享",
        r"opt.?out", r"选择退出", r"limit\s+the\s+use",
        r"global\s+privacy\s+control", r"gpc",
    ]
    _SPI_PATTERNS = [
        r"sensitive\s+personal\s+information", r"敏感个人信息",
        r"health\s+data", r"biometric", r"生物特征",
        r"precise\s+geo?location", r"精确位置",
    ]
    _DSR_CHANNEL_PATTERNS = [
        (r"toll.?free|免费电话|800.?\d{3}", "toll_free_phone"),
        (r"email|邮箱|电子邮箱|e.?mail", "email"),
        (r"web\s*form|online\s*form|在线表单|online\s*portal", "web_form"),
    ]
    _CATEGORY_PATTERNS = [
        (r"personal\s+identifier|个人标识符", "personal_identifier"),
        (r"health|medical|健康|医疗", "health_data"),
        (r"biometric|fingerprint|face|生物|指纹|人脸", "biometric_information"),
        (r"geo?location|位置|GPS", "precise_geolocation"),
        (r"financial|credit|金融|支付", "financial_account"),
        (r"email|password|credential|邮箱|密码|凭证", "account_credentials"),
        (r"race|ethnic|种族|族裔", "racial_or_ethnic_origin"),
    ]

    def __init__(self, parser: FileParser | None = None) -> None:
        self.parser = parser or FileParser()

    def extract(self, attachment: CPRAAttachment) -> dict[str, Any]:
        if attachment.file_format == "url":
            return {"role": attachment.file_role, "url_only": True}

        text = ""
        try:
            text = self.parser.parse_text(attachment.storage_uri)
        except Exception:
            return {"role": attachment.file_role, "parse_error": True}

        t = text.lower()

        if attachment.file_role == "privacy_policy":
            return self._extract_privacy_policy(t)
        elif attachment.file_role == "rights_sop":
            return self._extract_rights_sop(t)
        elif attachment.file_role == "data_map":
            return self._extract_data_map(t)
        elif attachment.file_role == "vendor_list":
            return self._extract_vendor_list(t)
        return {"role": attachment.file_role, "text_length": len(text)}

    def _extract_privacy_policy(self, t: str) -> dict[str, Any]:
        return {
            "role": "privacy_policy",
            "has_category_disclosure": bool(re.search(r"(?:we\s+collect|个人信息.*类别|data\s+categories)", t, re.IGNORECASE)),
            "has_purpose_disclosure": bool(re.search(r"(?:purpose|we\s+use|处理目的|使用目的)", t, re.IGNORECASE)),
            "has_retention_disclosure": bool(re.search(r"(?:retain|retention|保存期限|留存)", t, re.IGNORECASE)),
            "has_spi_statement": any(re.search(p, t, re.IGNORECASE) for p in self._SPI_PATTERNS),
            "has_opt_out_link": any(re.search(p, t, re.IGNORECASE) for p in self._OPT_OUT_PATTERNS),
            "has_limit_spi_link": bool(re.search(r"limit\s+the\s+use|limit.*sensitive|限制.*敏感.*使用", t, re.IGNORECASE)),
            "has_dsr_instructions": bool(re.search(r"(?:rights|request|access.*delete|权利请求|删除权)", t, re.IGNORECASE)),
            "has_toll_free_phone": bool(re.search(r"toll.?free|免费电话|800.?\d{3}", t, re.IGNORECASE)),
        }

    def _extract_rights_sop(self, t: str) -> dict[str, Any]:
        resp_days = None
        m = re.search(r"(\d+)\s*(?:days|天|日|business\s*days)", t, re.IGNORECASE)
        if m:
            resp_days = int(m.group(1))
        return {
            "role": "rights_sop",
            "response_days": resp_days,
            "supports_access": bool(re.search(r"access|访问|查阅|know", t, re.IGNORECASE)),
            "supports_delete": bool(re.search(r"delete|删除|erasure", t, re.IGNORECASE)),
            "supports_correct": bool(re.search(r"correct|更正|rectif", t, re.IGNORECASE)),
            "supports_opt_out": any(re.search(p, t, re.IGNORECASE) for p in self._OPT_OUT_PATTERNS),
            "has_verification_process": bool(re.search(r"verif|验证|身份确认", t, re.IGNORECASE)),
            "has_extension_procedure": bool(re.search(r"extension|延期|extend|additional.*45", t, re.IGNORECASE)),
        }

    def _extract_data_map(self, t: str) -> dict[str, Any]:
        categories: list[str] = []
        for pat, name in self._CATEGORY_PATTERNS:
            if re.search(pat, t, re.IGNORECASE):
                categories.append(name)
        spi_cats = [c for c in categories if c not in ("personal_identifier",)]
        return {
            "role": "data_map",
            "categories": categories,
            "spi_categories": spi_cats,
            "has_purposes": bool(re.search(r"(?:purpose|目的|used\s+for)", t, re.IGNORECASE)),
            "has_recipients": bool(re.search(r"(?:recipient|接收方|shared\s+with|disclosed\s+to)", t, re.IGNORECASE)),
            "has_retention": bool(re.search(r"(?:retention|留存|保存)", t, re.IGNORECASE)),
        }

    def _extract_vendor_list(self, t: str) -> dict[str, Any]:
        vendor_names = re.findall(r"(?:vendor|供应商|partner|合作伙伴|recipient)[：:\s]*([A-Za-z0-9\s&\.]{3,40})", t, re.IGNORECASE)
        return {
            "role": "vendor_list",
            "vendor_count": len(vendor_names) or t.count("\n"),
            "vendors": vendor_names[:20],
            "has_dpa_mentions": bool(re.search(r"dpa|data\s+processing\s+agreement|数据处理协议", t, re.IGNORECASE)),
            "has_service_provider": bool(re.search(r"service\s+provider|服务提供商", t, re.IGNORECASE)),
            "has_contractor": bool(re.search(r"contractor|承包商", t, re.IGNORECASE)),
        }
