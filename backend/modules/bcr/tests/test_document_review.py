"""Regression test matrix for BCR document-driven review."""

from __future__ import annotations

from backend.modules.bcr.bcr_checklist_checker import BCRChecklistChecker
from backend.modules.bcr.bcr_document_parser import BCRDocumentParser, BCRStructuredDocument
from backend.modules.bcr.bcr_risk_aggregator import BCRRiskAggregator
from backend.modules.bcr.bcr_rulebook_loader import BCRRulebookLoader
from backend.modules.bcr.bcr_type_classifier import BCRTypeClassifier

# ═══════════════════════════════════════════════════════════════════════
# Test Case 1: BCR-C basic — covers most requirements but TIA vague
# ═══════════════════════════════════════════════════════════════════════

_TEST_CASE_1 = """
GlobalTech Inc.
Binding Corporate Rules (Controllers)
Version 2.0
Effective January 1, 2024

1. Definitions
"BCR" means these Binding Corporate Rules for Controllers.

2. Scope
These BCR apply to all GlobalTech group members listed in Annex I.

3. Binding Nature
These BCR are legally binding on all GlobalTech group members and employees.
All members shall enter into an intra-group agreement to ensure compliance.

4. Third Party Beneficiary Rights
Data subjects shall have the right to enforce these BCR as third-party
beneficiaries against the EU liable entity and any BCR member.

5. EU Liable Entity
GlobalTech EU GmbH (Germany) is designated as the EU liable entity
and accepts liability for breaches of these BCR.

6. Data Protection Principles
Personal data shall be processed lawfully, fairly and in a transparent manner.
Data shall be collected for specified, explicit and legitimate purposes.
Processing shall be limited to what is necessary (data minimization).
Data shall be kept accurate and up to date. Storage shall be limited.

7. Data Subject Rights
Data subjects may exercise their rights of access, rectification, erasure,
restriction, portability and objection.

8. Complaint Handling
Data subjects may lodge complaints with the Group Data Protection Office.
Complaints will be handled as appropriate and responded to where feasible.

9. Cooperation with Supervisory Authorities
The group shall cooperate with supervisory authorities.

10. Onward Transfer
Personal data shall not be transferred to third parties outside the group
without adequate safeguards. Appropriate safeguards shall be put in place.

11. Third Country Law Assessment
Local laws in third countries shall be assessed as appropriate.

12. Audit and Training
Regular audits shall be conducted. Staff shall receive data protection training.

13. Update Mechanism
These BCR shall be updated as necessary.

14. Liability and Compensation
The EU liable entity shall be liable for breaches.

15. Termination
Members may withdraw from these BCR subject to conditions.
"""

_TEST_CASE_1_EXPECTED = [
    "complaint",       # complaint handling vague
    "third country",   # TIA vague
    "TIA.*方法|TIA.*method",  # TIA method incomplete
]


# ═══════════════════════════════════════════════════════════════════════
# Test Case 2: BCR-C HIGH RISK — missing critical requirements
# ═══════════════════════════════════════════════════════════════════════

_TEST_CASE_2 = """
DataFlow Corp.
Binding Corporate Rules (Controllers)

1. Scope
These BCR apply to DataFlow group companies.

2. Data Protection
Personal data shall be protected according to applicable law.

3. Data Subject Rights
Data subjects have rights under applicable law.

4. Complaint Handling
Complaints may be directed to the local office.

5. Updates
These BCR may be updated from time to time.

6. Termination
Members may withdraw subject to agreement.
"""

_TEST_CASE_2_EXPECTED = [
    "third party beneficiary",  # missing
    "eu liable|liable entity|责任主体",  # missing EU liable entity
    "binding|约束力",           # missing binding nature
    "onward|transfer",          # missing onward transfer
]


# ═══════════════════════════════════════════════════════════════════════
# Test Case 3: BCR MISMATCH — BCR-C title but BCR-P body
# ═══════════════════════════════════════════════════════════════════════

_TEST_CASE_3 = """
CloudServe Ltd.
Binding Corporate Rules (Controllers)

1. Scope
These BCR apply to CloudServe group members that process personal data
on behalf of our clients as a data processor according to documented
instructions received from those data controllers.

2. Processing Instructions
Members shall only process personal data on documented instructions
from the relevant controller. Members shall not process personal data
for their own purposes.

3. Sub-Processor Engagement
Members may engage sub-processors only with prior written authorisation
from the controller and subject to equivalent data protection obligations
pursuant to Article 28 of the GDPR.

4. Security
Members shall implement appropriate technical and organisational measures
to ensure a level of security appropriate to the risk.

5. Cooperation
Members shall cooperate with the controller and assist the controller
in complying with its obligations under Articles 32-36 GDPR.
"""

_TEST_CASE_3_EXPECTED = [
    "mismatch",   # BCR type mismatch
    "BCR-P",      # actually BCR-P
]


# ═══════════════════════════════════════════════════════════════════════
# Test runner
# ═══════════════════════════════════════════════════════════════════════

def _run_pipeline(text: str, declared_type: str | None):
    loader = BCRRulebookLoader()
    classifier = BCRTypeClassifier(rulebook_loader=loader)
    checker = BCRChecklistChecker(rulebook_loader=loader)
    aggregator = BCRRiskAggregator(rulebook=loader)

    # Build a simple parsed doc
    doc = BCRStructuredDocument(file_id="f1", filename="test.txt", plain_text=text)

    # Type classification
    type_class = classifier.classify(text, declared_type)
    bcr_type = type_class.actual_bcr_type if type_class.actual_bcr_type != "unknown" else "BCR-C"

    # Checklist
    findings, missing = checker.check(doc, bcr_type)

    # Aggregate
    agg = aggregator.aggregate(findings, missing, type_class)
    return {"type_class": type_class, "findings": findings, "missing": missing, "agg": agg}


def _check_hits(results, expected_patterns):
    import re
    all_text = results["agg"].get("overall_rating", "")
    for f in results["findings"]:
        all_text += f" {f.title} {f.finding}"
    for m in results["missing"]:
        all_text += f" {m}"
    hits = {}
    for pat in expected_patterns:
        hits[pat] = bool(re.search(pat, all_text, re.IGNORECASE))
    return hits


def test_regression_case_1_bcr_c_basic():
    res = _run_pipeline(_TEST_CASE_1, "BCR-C")
    hits = _check_hits(res, _TEST_CASE_1_EXPECTED)
    hit_count = sum(1 for v in hits.values() if v)
    print(f"  Case 1 hits: {hit_count}/{len(_TEST_CASE_1_EXPECTED)}")
    for pat, found in hits.items():
        print(f"    {'✓' if found else '✗'} {pat}")
    rate = res["agg"]["overall_rating"]
    print(f"  Rating: {rate}")
    assert hit_count >= 2, f"Expected ≥2 hits, got {hit_count}"


def test_regression_case_2_bcr_c_high_risk():
    res = _run_pipeline(_TEST_CASE_2, "BCR-C")
    hits = _check_hits(res, _TEST_CASE_2_EXPECTED)
    hit_count = sum(1 for v in hits.values() if v)
    print(f"  Case 2 hits: {hit_count}/{len(_TEST_CASE_2_EXPECTED)}")
    for pat, found in hits.items():
        print(f"    {'✓' if found else '✗'} {pat}")
    rate = res["agg"]["overall_rating"]
    print(f"  Rating: {rate}")
    assert hit_count >= 3, f"Expected ≥3 hits, got {hit_count}"


def test_regression_case_3_bcr_mismatch():
    res = _run_pipeline(_TEST_CASE_3, "BCR-C")
    hits = _check_hits(res, _TEST_CASE_3_EXPECTED)
    hit_count = sum(1 for v in hits.values() if v)
    print(f"  Case 3 hits: {hit_count}/{len(_TEST_CASE_3_EXPECTED)}")
    for pat, found in hits.items():
        print(f"    {'✓' if found else '✗'} {pat}")
    tc = res["type_class"]
    print(f"  Type: {tc.actual_bcr_type} consistency={tc.type_consistency} risk={tc.risk_level}")
    assert tc.type_consistency == "mismatch" or tc.actual_bcr_type == "BCR-P", f"Got {tc.type_consistency}, {tc.actual_bcr_type}"
