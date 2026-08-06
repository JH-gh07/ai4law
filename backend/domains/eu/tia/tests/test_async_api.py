import time



def test_tia_async_flow(authenticated_client) -> None:
    accepted = authenticated_client.post(
        "/api/v1/tia/generate_async",
        json={
            "transfer_tool": "scc",
            "data_exporter_profile": "EU Exporter A",
            "data_importer_profile": "US Importer B",
            "third_country_assessment": "存在政府访问风险",
            "supplementary_measures": "端到端加密、严格密钥管理、访问透明报告",
            "final_conclusion": "在补充措施生效前提下SCC可传输",
            "attachments": [
                {
                    "file_role": "transfer_agreement",
                    "file_name": "agreement.pdf",
                    "file_format": "pdf",
                    "storage_uri": "storage://uploads/agreement.pdf",
                }
            ],
        },
    )
    assert accepted.status_code == 200
    task_id = accepted.json()["task_id"]

    # TIA makes ~9 LLM calls (rag_planning + attachment_review + 6×generate_chapter + dpo_review)
    # Each call takes ~20-30s with DeepSeek-V3.2, so total runtime is ~4-5 minutes
    for _ in range(3000):  # 3000 × 0.1s = 300s (5 min) timeout for real LLM calls
        status = authenticated_client.get(f"/api/v1/tia/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()
        if payload["state"] == "COMPLETED":
            assert payload["result"]["report_path"].endswith(".docx")
            return
        if payload["state"] == "FAILED":
            raise AssertionError(payload)
        time.sleep(0.1)

    raise AssertionError("tia async task timeout")
