"""EU SCC rule engine — deterministic compliance review under GDPR / EU 2021/914.

Five review components:
1. Module selection validator (C2C/C2P/P2P/P2C)
2. Standard clause comparator (vs EU 2021/914)
3. Annex reviewer (I.A, I.B, II, III)
4. TIA / supplementary measures reviewer
5. Overall risk scoring
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.domains.eu.scc_review.schema import (
    SCCAnnexIA,
    SCCAnnexIB,
    SCCAnnexII,
    SCCAnnexIII,
    SCCClause,
    SCCDocument,
    SCCFinding,
    SCCRuleEngineResult,
    SCCTransferChain,
    AnnexReview,
    ClauseComparison,
    ModuleValidation,
    TIAReview,
)

# ═══════════════════════════════════════════════════════════════════════
# EU 2021/914 — Standard Clause Text (abbreviated key provisions)
# ═══════════════════════════════════════════════════════════════════════

_STANDARD_CLAUSE_KEY_PROVISIONS: dict[int, dict[str, str]] = {
    7: {
        "docking": "Additional parties may accede to these Clauses throughout the life-cycle of the contract.",
        "consent": "Changes to the agreed-upon list of additional parties may only be made with the prior consent of the data exporter.",
    },
    9: {
        "authorization": "The data importer shall not sub-contract any of its processing activities without the data exporter's prior specific written authorization.",
        "list": "The data importer shall maintain an up-to-date list of sub-processors and make it available to the data exporter.",
        "notification": "The data importer shall inform the data exporter of any intended changes concerning the addition or replacement of sub-processors.",
    },
    14: {
        "assessment": "The Parties warrant that they have no reason to believe that the laws and practices in the third country of destination prevent the data importer from fulfilling its obligations under these Clauses.",
        "documentation": "The data importer shall document the specific circumstances of the transfer and the assessment carried out.",
        "notification": "The data importer agrees to notify the data exporter if it has reason to believe that it is or has become subject to laws not in line with the requirements under paragraph (a).",
    },
    15: {
        "notification": "The data importer shall promptly notify the data exporter if it receives a legally binding request from a public authority to disclose personal data transferred pursuant to these Clauses.",
        "review": "The data impporter shall review the legality of the request and challenge it if it reasonably considers that there are grounds to do so.",
        "information": "The data importer shall provide the data exporter with as much relevant information as possible.",
        "transparency": "The data importer shall document its assessment and make it available to the competent supervisory authority on request.",
    },
    16: {
        "deletion": "Following termination of the provision of the processing services, the data importer shall, at the choice of the data exporter, delete all personal data or return them to the data exporter.",
        "certification": "The data importer shall certify in writing that it has fully complied with this obligation.",
    },
    17: {
        "liability": "Each Party shall be liable to the other Party for any damages it causes the other Party by any breach of these Clauses.",
        "indemnification": "The data importer shall indemnify the data exporter and hold it harmless against any claims.",
    },
    18: {
        "governing_law": "These Clauses shall be governed by the law of one of the EU Member States, provided such law allows for third-party beneficiary rights.",
        "jurisdiction": "Any dispute arising from these Clauses shall be resolved by the courts of an EU Member State.",
    },
}

# Weakening signals — patterns that indicate a clause has been weakened
_WEAKENING_SIGNALS: dict[str, list[tuple[str, str, str]]] = {
    "Clause 15(a) notification": [
        (r"as\s+soon\s+as\s+(?:legally\s+)?permissible", "修改为'法律许可时'通知，而非'立即(promptly)'", "restore 'promptly notify'"),
        (r"without\s+undue\s+delay\s+to\s+the\s+extent\s+legally\s+permissible", "增加法律许可限定条件", "restore unconditional prompt notification"),
        (r"subject\s+to\s+applicable\s+(?:local\s+)?law", "受限于当地法律，可能削弱通知义务", "restore unconditional obligation"),
    ],
    "Clause 15(b) review": [
        (r"at\s+(?:its|the\s+data\s+importer[´'’]?s)\s+(?:sole\s+)?discretion", "将审查义务改为酌情处理", "restore mandatory review obligation"),
        (r"if\s+it\s+(?:reasonably\s+)?considers\s+(?:it\s+to\s+be\s+)?appropriate", "降低审查标准", "restore 'reasonably considers there are grounds'"),
        (r"reserves?\s+the\s+right", "保留了选择权，而非承担审查义务", "make review obligation mandatory"),
    ],
    "Clause 15(c) information": [
        (r"at\s+(?:the\s+data\s+importer[´'’]?s\s+)?discretion", "信息提供改为酌情处理", "restore 'as much relevant information as possible'"),
        (r"to\s+the\s+extent\s+(?:reasonably\s+)?practicable", "增加合理可行限定条件", "restore full disclosure obligation"),
    ],
    "Clause 14 assessment": [
        (r"to\s+the\s+best\s+of\s+(?:its|the\s+data\s+importer[´'’]?s)\s+knowledge", "将评估义务降低为'据其所知'", "restore objective assessment obligation"),
        (r"no\s+independent\s+(?:assessment|obligation)", "明确否认独立评估义务", "restore assessment obligation"),
    ],
    "Clause 9 authorization": [
        (r"general\s+(?:written\s+)?authori[sz]ation", "改为一般授权而非具体授权", "require specific prior authorization"),
        (r"objection\s+(?:period|within)\s*[:]?\s*\d+\s*(?:business\s+)?days?", "objection窗口过短 → 检查是否合理", "verify objection period is reasonable"),
    ],
}

# Third country adequacy decisions (partial list)
_THIRD_COUNTRY_ADEQUACY = {
    "united kingdom": True,
    "uk": True,
    "japan": True,
    "south korea": True,
    "republic of korea": True,
    "switzerland": True,
    "canada": True,
    "argentina": True,
    "israel": True,
    "new zealand": True,
    "uruguay": True,
    "andorra": True,
    "faroe islands": True,
    "guernsey": True,
    "jersey": True,
    "isle of man": True,
    "united states": False,
    "usa": False,
    "india": False,
    "serbia": False,
    "china": False,
    "russia": False,
    "brazil": False,
    "singapore": False,
    "australia": False,
}

# Schrems II supplementary measures — technical
_SCHREMS_II_TECHNICAL_MEASURES = [
    "end-to-end encryption", "e2e encryption", "端到端加密",
    "hold your own key", "customer-managed keys", "client-side encryption",
    "eu-held encryption keys", "欧盟持钥", "byok",
    "data-at-rest encryption with eu-controlled keys",
    "zero-access encryption", "zero knowledge encryption",
]

# Schrems II supplementary measures — contractual
_SCHREMS_II_CONTRACTUAL_MEASURES = [
    "government access notification", "政府访问通知",
    "challenge unlawful requests", "挑战非法请求",
    "transparency report", "透明度报告",
    "warrant canary",
    "commitment to challenge surveillance requests",
]

# Schrems II supplementary measures — organizational
_SCHREMS_II_ORGANIZATIONAL_MEASURES = [
    "data minimization and retention limits",
    "independent annual audit", "独立年度审计",
    "privacy impact assessment for government access",
    "separation of duties for key management",
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


# ═══════════════════════════════════════════════════════════════════════
# 1. Module Selection Validator
# ═══════════════════════════════════════════════════════════════════════

def validate_module_selection(
    chain: SCCTransferChain,
    declared_module: str,
) -> ModuleValidation:
    """Validate SCC Module selection (One/Two/Three/Four) against party roles."""
    exp = _normalize(chain.exporter_role)
    imp = _normalize(chain.importer_role)

    if "controller" in exp and "controller" in imp:
        expected = "Module One"
    elif "controller" in exp and "processor" in imp:
        expected = "Module Two"
    elif "processor" in exp and "processor" in imp:
        expected = "Module Three"
    elif "processor" in exp and "controller" in imp:
        expected = "Module Four"
    else:
        expected = ""  # cannot determine

    actual = declared_module
    is_correct = _normalize(actual) == _normalize(expected)

    reason = ""
    if not is_correct and expected:
        reason = (
            f"Exporter role '{chain.exporter_role}' + Importer role '{chain.importer_role}' "
            f"→ expected {expected}, but document declares {declared_module}."
        )

    return ModuleValidation(
        expected_module=expected,
        actual_module=actual,
        is_correct=is_correct,
        mismatch_reason=reason,
    )


# ═══════════════════════════════════════════════════════════════════════
# 2. Standard Clause Comparator
# ═══════════════════════════════════════════════════════════════════════

def _check_clause_deviation(clause: SCCClause) -> SCCFinding | None:
    """Check a single clause for deviations from EU 2021/914 standard."""
    content_norm = _normalize(clause.content)
    if not content_norm:
        return None

    for label, signals in _WEAKENING_SIGNALS.items():
        clause_ref = label.split(" ")[0] + " " + label.split(" ", 2)[-1] if " " in label else label
        refs = re.findall(r"Clause\s+(\d+)[\(（]\s*([a-zA-Z0-9]+)\s*[\)）]", label)
        if refs:
            cl_no = refs[0][0]
            sub = refs[0][1] if len(refs[0]) > 1 else ""
            clause_ref = f"{cl_no}({sub})" if sub else cl_no

        for pattern, risk_desc, suggestion in signals:
            if re.search(pattern, clause.content, re.IGNORECASE):
                return SCCFinding(
                    finding_id=f"EU-SCC-CLAUSE-{clause.clause_no}-DEVIATION",
                    location=label,
                    clause_ref=clause_ref,
                    original_text=re.search(pattern, clause.content, re.IGNORECASE).group(0)[:200] if re.search(pattern, clause.content, re.IGNORECASE) else "",
                    issue_type="clause_weakened",
                    severity="HIGH",
                    risk_analysis=f"Clause {clause.clause_no} deviation detected: {risk_desc}",
                    legal_basis="EU 2021/914, Recital 3 (invariability of Clauses); GDPR Article 46",
                    recommendation=suggestion,
                    suggested_text="Restore the standard EU 2021/914 text for this provision.",
                )

    return None


def compare_standard_clauses(doc: SCCDocument) -> ClauseComparison:
    """Compare document clauses against EU 2021/914 standard text."""
    findings: list[SCCFinding] = []
    clauses_checked = 0

    for clause in doc.clauses:
        if clause.clause_no == 0:
            continue
        clauses_checked += 1
        finding = _check_clause_deviation(clause)
        if finding:
            findings.append(finding)
            clause.has_deviation = True
            clause.deviation_type = "weakening" if finding.severity == "HIGH" else "restriction_added"
            clause.deviation_description = finding.risk_analysis

    return ClauseComparison(
        clauses_checked=clauses_checked,
        deviations_found=len(findings),
        findings=findings,
    )


# ═══════════════════════════════════════════════════════════════════════
# 3. Annex Reviewer
# ═══════════════════════════════════════════════════════════════════════

def review_annexes(doc: SCCDocument, declared_module: str) -> AnnexReview:
    """Review Annex I.A, I.B, II, III for completeness and accuracy."""
    findings: list[SCCFinding] = []

    # === Annex I.A — Parties ===
    if not doc.annex_i_a.parties:
        pass  # No parties found — parser may have missed them
    for party in doc.annex_i_a.parties:
        if party.is_incomplete:
            findings.append(SCCFinding(
                finding_id=f"EU-SCC-ANNEX-IA-INCOMPLETE-{party.name[:20]}",
                location="Annex I.A",
                clause_ref="Annex I.A",
                original_text=party.name,
                issue_type="party_info_incomplete",
                severity="MEDIUM",
                risk_analysis="Party information references external document (e.g., 'See MSA') rather than providing complete details directly in the SCC.",
                legal_basis="EU 2021/914 Annex I.A; GDPR Article 46(2)(c)",
                recommendation="Insert complete party name, address, contact person, and role directly in Annex I.A.",
                suggested_text="[Complete party details]",
            ))
        if not party.name or not party.role:
            findings.append(SCCFinding(
                finding_id=f"EU-SCC-ANNEX-IA-MISSING-FIELDS-{party.name[:20] or 'unknown'}",
                location="Annex I.A",
                clause_ref="Annex I.A",
                original_text="",
                issue_type="annex_incomplete",
                severity="MEDIUM",
                risk_analysis="Party name or role is missing from Annex I.A.",
                legal_basis="EU 2021/914 Annex I.A",
                recommendation="Complete all required party fields in Annex I.A.",
                suggested_text="[Complete fields]",
            ))

    # Check party count
    has_exporter = any(p.role and "export" in p.role.lower() or "controller" in p.role.lower() for p in doc.annex_i_a.parties)
    has_importer = any(p.role and "import" in p.role.lower() or "processor" in p.role.lower() for p in doc.annex_i_a.parties)
    if not (has_exporter and has_importer) and len(doc.annex_i_a.parties) >= 2:
        pass  # OK — two parties but roles not parsed
    elif len(doc.annex_i_a.parties) < 2:
        findings.append(SCCFinding(
            finding_id="EU-SCC-ANNEX-IA-MISSING-PARTIES",
            location="Annex I.A",
            clause_ref="Annex I.A",
            original_text="",
            issue_type="annex_incomplete",
            severity="MEDIUM" if declared_module in ("Module One", "Module Two") else "HIGH",
            risk_analysis="Less than 2 parties identified in Annex I.A. Docking Clause (Clause 7) parties may also be missing.",
            legal_basis="EU 2021/914 Annex I.A; Clause 7",
            recommendation="Complete Annex I.A with all data exporters and importers, including any additional parties via Docking Clause.",
            suggested_text="",
        ))

    # === Annex I.B — Transfer Description ===
    ib = doc.annex_i_b
    if ib.data_categories:
        if _normalize(ib.data_categories) in ("order history data", "order data", "customer data", "transaction data"):
            findings.append(SCCFinding(
                finding_id="EU-SCC-ANNEX-IB-VAGUE-CATEGORIES",
                location="Annex I.B",
                clause_ref="Annex I.B",
                original_text=ib.data_categories,
                issue_type="annex_vague",
                severity="LOW",
                risk_analysis=f"Data categories '{ib.data_categories}' are too vague and may not satisfy the specificity required by EU 2021/914.",
                legal_basis="EU 2021/914 Annex I.B; GDPR Article 5(1)(c) (data minimisation)",
                recommendation="Specify precise categories of personal data transferred (e.g., name, email, shipping address, purchase history, device identifiers).",
                suggested_text="",
            ))

    # Special category data check
    health_terms = ("health", "medical", "patient", "diagnosis", "clinical", "treatment", "disease", "prescription", "健康", "医疗", "病历")
    ib_text = _normalize(ib.data_categories + " " + ib.processing_purpose + " " + " ".join(ib.special_category_data))
    has_health_terms = any(t in ib_text for t in health_terms)
    has_special_declared = len(ib.special_category_data) > 0

    if has_health_terms and not has_special_declared:
        findings.append(SCCFinding(
            finding_id="EU-SCC-ANNEX-IB-MISCLASSIFIED-SPECIAL",
            location="Annex I.B",
            clause_ref="Annex I.B",
            original_text=ib.data_categories[:200],
            issue_type="special_category_misclassified",
            severity="HIGH",
            risk_analysis="Transfer description contains health/medical data terms but special category data is NOT declared. Under GDPR Article 9, health data requires explicit consent or another exemption, and SCCs alone may not be sufficient.",
            legal_basis="GDPR Article 9; EU 2021/914; EDPB Recommendations 01/2020",
            recommendation="(1) Verify whether the data includes special categories; (2) If yes, declare them explicitly in Annex I.B; (3) Assess whether supplementary measures are needed for special category data transfers.",
            suggested_text="",
        ))

    # === Annex II — Technical and Organisational Measures ===
    has_toms = len(doc.annex_ii.tom_items) > 0
    if not has_toms:
        findings.append(SCCFinding(
            finding_id="EU-SCC-ANNEX-II-EMPTY",
            location="Annex II",
            clause_ref="Annex II",
            original_text="",
            issue_type="annex_incomplete",
            severity="HIGH",
            risk_analysis="Annex II (Technical and Organisational Measures) appears empty or could not be parsed. Without specified TOMs, the SCC does not demonstrate adequate data protection safeguards.",
            legal_basis="EU 2021/914 Annex II; GDPR Articles 32, 46",
            recommendation="Complete Annex II with specific technical and organisational measures, including encryption standards, access controls, incident response, and data minimization practices.",
            suggested_text="",
        ))

    # === Annex III — Sub-Processors ===
    if not doc.annex_iii.sub_processors:
        pass  # May be empty legitimately

    return AnnexReview(findings=findings)


# ═══════════════════════════════════════════════════════════════════════
# 4. TIA / Supplementary Measures Reviewer
# ═══════════════════════════════════════════════════════════════════════

def review_tia_and_measures(
    chain: SCCTransferChain,
    doc: SCCDocument,
    has_tia: bool = False,
    has_supplementary_measures: bool = False,
) -> TIAReview:
    """Review TIA (Transfer Impact Assessment) and supplementary measures."""
    findings: list[SCCFinding] = []

    # Identify third country transfers
    third_country_locations: list[str] = []
    all_locations = set(chain.storage_locations + chain.access_locations + chain.onward_transfer_locations)
    for loc in all_locations:
        loc_norm = _normalize(loc)
        for country, is_adequate in _THIRD_COUNTRY_ADEQUACY.items():
            if country in loc_norm:
                if not is_adequate:
                    third_country_locations.append(loc)
                break

    has_third_country = len(third_country_locations) > 0

    # Check if Clause 14 exists and is intact
    clause_14 = next((c for c in doc.clauses if c.clause_no == 14), None)
    clause_14_weakened = clause_14.has_deviation if clause_14 else False

    # Check Schrems II supplementary measures (in Annex II)
    annex_ii_text = _normalize(" ".join(doc.annex_ii.tom_items) + " " + " ".join(doc.annex_ii.supplementary_measures))
    doc_text = _normalize(doc.raw_text)

    schrems_tech = any(kw in annex_ii_text or kw in doc_text for kw in _SCHREMS_II_TECHNICAL_MEASURES)
    schrems_contractual = any(kw in annex_ii_text or kw in doc_text for kw in _SCHREMS_II_CONTRACTUAL_MEASURES)
    schrems_org = any(kw in annex_ii_text or kw in doc_text for kw in _SCHREMS_II_ORGANIZATIONAL_MEASURES)

    # === TIA findings ===
    if has_third_country and not has_tia:
        findings.append(SCCFinding(
            finding_id="EU-SCC-TIA-MISSING",
            location="Clause 14",
            clause_ref="14",
            original_text="",
            issue_type="tia_missing",
            severity="HIGH",
            risk_analysis=(
                f"Third country transfer identified to: {', '.join(third_country_locations[:3])}. "
                f"No Transfer Impact Assessment (TIA) has been provided. Under GDPR and Schrems II "
                f"(C-311/18), a documented TIA is required before transferring personal data to a "
                f"third country without an adequacy decision."
            ),
            legal_basis="GDPR Article 46; Schrems II C-311/18; EDPB Recommendations 01/2020; EU 2021/914 Clause 14",
            recommendation=(
                f"Complete a TIA for transfers to {', '.join(third_country_locations[:3])}. "
                f"The TIA must: (1) assess the laws and practices of the destination country; "
                f"(2) evaluate whether they impinge on the SCCs' effectiveness; "
                f"(3) identify and implement supplementary measures as needed."
            ),
            suggested_text="",
        ))

    if has_third_country and clause_14_weakened:
        findings.append(SCCFinding(
            finding_id="EU-SCC-CLAUSE14-WEAKENED-THIRD",
            location="Clause 14",
            clause_ref="14",
            original_text=clause_14.content[:200] if clause_14 else "",
            issue_type="clause_weakened",
            severity="HIGH",
            risk_analysis="Clause 14 (local laws assessment) has been weakened while third country transfers exist. Combined with missing TIA, this creates an unacceptable compliance risk.",
            legal_basis="EU 2021/914 Clause 14; Schrems II C-311/18",
            recommendation="Restore standard Clause 14 text and complete a documented TIA before proceeding with third country transfers.",
            suggested_text="",
        ))

    # === Supplementary measures findings ===
    if has_third_country and not has_tia:
        findings.append(SCCFinding(
            finding_id="EU-SCC-SUPP-MEASURES-INSUFFICIENT",
            location="Annex II",
            clause_ref="Annex II & Clause 14",
            original_text="",
            issue_type="supplementary_measures_insufficient",
            severity="HIGH",
            risk_analysis=(
                f"Third country transfer to non-adequate jurisdiction '{', '.join(third_country_locations[:3])}' "
                f"requires Schrems II supplementary measures. Technical: {'found' if schrems_tech else 'NOT FOUND'}. "
                f"Contractual: {'found' if schrems_contractual else 'NOT FOUND'}. "
                f"Organizational: {'found' if schrems_org else 'NOT FOUND'}."
            ),
            legal_basis="Schrems II C-311/18; EDPB Recommendations 01/2020; EU 2021/914 Annex II",
            recommendation=(
                "Implement Schrems II supplementary measures: (1) Technical — end-to-end encryption with "
                "EU-held keys, zero-access architecture; (2) Contractual — government access notification "
                "obligation, commitment to challenge unlawful requests, transparency reporting; "
                "(3) Organizational — independent annual audit, data minimization."
            ),
            suggested_text="",
        ))

    # === US-specific findings ===
    us_locations = [l for l in all_locations if any(kw in _normalize(l) for kw in ("united states", "usa", "us", "amazon", "aws", "google cloud", "azure", "microsoft"))]
    if us_locations and not (schrems_tech and schrems_contractual):
        findings.append(SCCFinding(
            finding_id="EU-SCC-US-CLOUD-ACT-RISK",
            location="Annex II / TIA",
            clause_ref="Annex II & Clause 14",
            original_text="",
            issue_type="supplementary_measures_insufficient",
            severity="HIGH",
            risk_analysis=(
                f"Data appears to flow to US-based infrastructure ({', '.join(us_locations[:2])}). "
                f"US law (CLOUD Act, FISA 702) permits government access to data held by US cloud providers. "
                f"Supplementary measures addressing US-specific surveillance risks are missing or insufficient."
            ),
            legal_basis="Schrems II C-311/18; CLOUD Act 18 U.S.C. § 2713; FISA 702; EDPB Recommendations 01/2020",
            recommendation=(
                "For US-based transfers: (1) implement end-to-end encryption with EU-held keys; "
                "(2) ensure the data importer cannot access plaintext data; "
                "(3) add contractual commitments to challenge FISA 702 orders and notify the exporter; "
                "(4) publish a transparency report on government access requests."
            ),
            suggested_text="",
        ))

    # === Sub-processor chain review ===
    if chain.sub_processors:
        for sp_name in chain.sub_processors:
            sp_norm = _normalize(sp_name)
            for country, is_adequate in _THIRD_COUNTRY_ADEQUACY.items():
                if country in sp_norm and not is_adequate:
                    findings.append(SCCFinding(
                        finding_id=f"EU-SCC-SUBPROC-THIRD-{sp_name[:20].replace(' ', '-').upper()}",
                        location="Annex III / Clause 9",
                        clause_ref="Annex III & Clause 9",
                        original_text=sp_name,
                        issue_type="sub_processor_chain_incomplete",
                        severity="MEDIUM",
                        risk_analysis=f"Sub-processor '{sp_name}' is in a non-adequate third country. Verify: (1) authorization under Clause 9; (2) that the SCC covers onward transfers; (3) that TIA covers this sub-processor.",
                        legal_basis="EU 2021/914 Clause 9; GDPR Article 28; Schrems II C-311/18",
                        recommendation=f"Ensure Clause 9 authorization for '{sp_name}' and include in TIA and supplementary measures assessment.",
                        suggested_text="",
                    ))

    return TIAReview(
        has_third_country_transfer=has_third_country,
        third_country_transfers=third_country_locations,
        tia_present=has_tia,
        has_supplementary_measures=has_supplementary_measures,
        schrems_ii_measures_present=schrems_tech and schrems_contractual,
        findings=findings,
    )


# ═══════════════════════════════════════════════════════════════════════
# 5. Overall Risk Scoring
# ═══════════════════════════════════════════════════════════════════════

def score_scc_risk(all_findings: list[SCCFinding]) -> str:
    """Calculate overall SCC compliance risk rating.

    Multi-dimensional: takes the worst severity extended by rule context.
    NOT based on PII/SPI count thresholds.
    """
    severities = {f.severity for f in all_findings}

    if "HIGH" in severities:
        return "HIGH"
    if "MEDIUM" in severities:
        return "MEDIUM"
    return "LOW"


# ═══════════════════════════════════════════════════════════════════════
# Main rule engine entry point
# ═══════════════════════════════════════════════════════════════════════

def run_eu_scc_rule_engine(
    doc: SCCDocument,
    chain: SCCTransferChain,
    declared_module: str,
    has_tia: bool = False,
    has_supplementary_measures: bool = False,
) -> SCCRuleEngineResult:
    """Execute all EU SCC review stages and return complete result."""

    # 1. Module validation
    module_val = validate_module_selection(chain, declared_module)

    # 2. Clause comparison
    clause_comp = compare_standard_clauses(doc)

    # 3. Annex review
    annex_rev = review_annexes(doc, declared_module)

    # 4. TIA / supplementary measures review
    tia_rev = review_tia_and_measures(chain, doc, has_tia, has_supplementary_measures)

    # Collect all findings
    all_findings: list[SCCFinding] = []
    if not module_val.is_correct:
        all_findings.append(SCCFinding(
            finding_id="EU-SCC-MODULE-MISMATCH",
            location="Document Header",
            clause_ref="Module Type",
            original_text=module_val.actual_module,
            issue_type="module_mismatch",
            severity="HIGH",
            risk_analysis=module_val.mismatch_reason,
            legal_basis="EU 2021/914; GDPR Article 46",
            recommendation=f"Use {module_val.expected_module} instead of {module_val.actual_module}, or verify that the party roles in Annex I.A match the declared module.",
            suggested_text="",
        ))
    all_findings.extend(clause_comp.findings)
    all_findings.extend(annex_rev.findings)
    all_findings.extend(tia_rev.findings)

    # 5. Overall risk score
    overall_rating = score_scc_risk(all_findings)

    return SCCRuleEngineResult(
        document=doc,
        transfer_chain=chain,
        module_validation=module_val,
        clause_comparison=clause_comp,
        annex_review=annex_rev,
        tia_review=tia_rev,
        all_findings=all_findings,
        overall_rating=overall_rating,
    )
