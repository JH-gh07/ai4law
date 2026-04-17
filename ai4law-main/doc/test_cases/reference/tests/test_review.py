from io import BytesIO

from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from backend.services.file_service import FileService


def build_docx_bytes(paragraphs: list[str]) -> bytes:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    handle = BytesIO()
    document.save(handle)
    return handle.getvalue()


def build_pdf_bytes() -> bytes:
    handle = BytesIO()
    pdf = canvas.Canvas(handle, pagesize=letter)
    pdf.drawString(72, 720, "Clause 1 Data processing purpose")
    pdf.drawString(72, 700, "The processing purpose is customer service and basic information handling.")
    pdf.save()
    return handle.getvalue()


def sample_contract_bytes() -> bytes:
    return build_docx_bytes(
        [
            "第一条 数据出境安排",
            "乙方应将相关个人信息传输至境外系统，但未说明接收方联系方式，也未写明存储地点。",
            "第二条 安全措施",
            "乙方应在必要时采取安全措施，并及时响应。",
            "第三条 责任承担",
            "乙方承担全部责任，并赔偿甲方全部损失。",
        ]
    )


def test_review_report_mode_workflow(client):
    create_response = client.post(
        "/api/v1/review/tasks",
        json={
            "review_mode": "REPORT",
            "contract_type": "PERSONAL_INFO_SCC",
            "review_stance": "PARTY_A",
            "custom_rule_text": "重点检查审计权和备案配套义务",
            "custom_rule_ids": ["OUTBOUND_FILING_FOCUS"],
        },
    )
    assert create_response.status_code == 200
    task = create_response.json()
    assert task["review_mode"] == "REPORT"

    files = {
        "file": (
            "review.docx",
            sample_contract_bytes(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    upload_response = client.post(f"/api/v1/review/tasks/{task['id']}/files", files=files)
    assert upload_response.status_code == 200

    analyze_response = client.post(f"/api/v1/review/tasks/{task['id']}/analyze")
    assert analyze_response.status_code == 200
    assert analyze_response.json()["status"] == "COMPLETED"

    status_response = client.get(f"/api/v1/review/tasks/{task['id']}/status")
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["summary"]["overall_rating"] in {"高风险", "中风险", "低风险"}
    assert payload["artifacts"]["report_ready"] is True
    assert payload["contract_type"] == "PERSONAL_INFO_SCC"
    assert payload["custom_rules"]["text"] == "重点检查审计权和备案配套义务"

    issues_response = client.get(f"/api/v1/review/tasks/{task['id']}/issues")
    assert issues_response.status_code == 200
    issues = issues_response.json()["issues"]
    assert len(issues) >= 1
    assert any(issue["problem_type"] == "CUSTOM_RULE_FOCUS" for issue in issues)

    report_response = client.get(f"/api/v1/review/tasks/{task['id']}/report")
    assert report_response.status_code == 200
    report_payload = report_response.json()
    assert report_payload["report"]["artifact_type"] == "docx"
    assert report_payload["report_content"]["title"] == "数据出境合同合规审查报告"
    assert any("个人信息保护法" in citation or "标准合同" in citation for issue in issues for citation in issue["citation_sources"])


def test_review_redline_mode_outputs_revised_contract_and_diff(client):
    create_response = client.post(
        "/api/v1/review/tasks",
        json={
            "review_mode": "REDLINE",
            "contract_type": "PERSONAL_INFO_SCC",
            "review_stance": "PARTY_B",
        },
    )
    task_id = create_response.json()["id"]

    files = {
        "file": (
            "redline.docx",
            sample_contract_bytes(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    upload_response = client.post(f"/api/v1/review/tasks/{task_id}/files", files=files)
    assert upload_response.status_code == 200

    analyze_response = client.post(f"/api/v1/review/tasks/{task_id}/analyze")
    assert analyze_response.status_code == 200
    assert analyze_response.json()["review_mode"] == "REDLINE"

    revised_response = client.get(f"/api/v1/review/tasks/{task_id}/revised-contract")
    assert revised_response.status_code == 200
    revised_payload = revised_response.json()
    assert revised_payload["artifact"]["artifact_type"] == "docx"
    assert revised_payload["diff_count"] >= 1

    diff_response = client.get(f"/api/v1/review/tasks/{task_id}/diff")
    assert diff_response.status_code == 200
    diff_items = diff_response.json()["items"]
    assert len(diff_items) >= 1
    assert any(item["action"] in {"MODIFY", "REWRITE", "APPEND_APPENDIX"} for item in diff_items)


def test_review_stance_changes_issue_detection(client):
    files = {
        "file": (
            "stance.docx",
            sample_contract_bytes(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }

    party_a_task = client.post(
        "/api/v1/review/tasks",
        json={"review_mode": "REPORT", "contract_type": "GENERAL_CONTRACT", "review_stance": "PARTY_A"},
    ).json()["id"]
    client.post(f"/api/v1/review/tasks/{party_a_task}/files", files=files)
    client.post(f"/api/v1/review/tasks/{party_a_task}/analyze")
    issues_a = client.get(f"/api/v1/review/tasks/{party_a_task}/issues").json()["issues"]

    party_b_task = client.post(
        "/api/v1/review/tasks",
        json={"review_mode": "REPORT", "contract_type": "GENERAL_CONTRACT", "review_stance": "PARTY_B"},
    ).json()["id"]
    client.post(f"/api/v1/review/tasks/{party_b_task}/files", files=files)
    client.post(f"/api/v1/review/tasks/{party_b_task}/analyze")
    issues_b = client.get(f"/api/v1/review/tasks/{party_b_task}/issues").json()["issues"]

    assert not any(issue["title"] == "乙方责任明显过重" for issue in issues_a)
    assert any(issue["title"] == "乙方责任明显过重" for issue in issues_b)


def test_file_service_extracts_pdf_text(tmp_path):
    from backend.core.settings import Settings

    settings = Settings(storage_dir=tmp_path / "storage")
    service = FileService(settings)
    path = tmp_path / "sample.pdf"
    path.write_bytes(build_pdf_bytes())
    text = service.extract_text(path)
    assert "Data processing purpose" in text
