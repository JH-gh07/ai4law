# Diagnosis Module

## Purpose
Rule-based compliance path diagnosis for cross-border data transfer.

## Endpoints
- `POST /api/v1/diagnosis/evaluate`
- `POST /api/v1/diagnosis/report`

`/diagnosis/report` 输出：
- `report_path`（当前指向 HTML 预览文件）
- `html_report_path`
- `pdf_report_path`
- `output_files`（`html`、`pdf`）

## Example
```bash
curl -X POST http://127.0.0.1:8000/api/v1/diagnosis/evaluate \
  -H 'Content-Type: application/json' \
  -d '{
    "q1_is_ciio":"no",
    "q2_has_important_data":"no",
    "q3_pii_count":200000,
    "q4_spi_count":800,
    "q5_no_personal_info":"no",
    "q6_scenario":"contract_performance",
    "q7_receiver_type":"third_party",
    "q8_purpose":"global crm sync"
  }'
```
