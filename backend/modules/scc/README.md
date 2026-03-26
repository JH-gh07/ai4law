# SCC Module

## Purpose
Generate PIPIA report for SCC/certification route.

## Endpoint
- `POST /api/v1/scc/generate`
- `POST /api/v1/scc/generate_async`
- `GET /api/v1/scc/tasks/{task_id}`
- `POST /api/v1/scc/tasks/{task_id}/retry`

输出：
- `report_path`：docx 文件路径
- `output_files.markdown`：md 文件路径

## Example
```bash
curl -X POST http://127.0.0.1:8000/api/v1/scc/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "company_name":"示例科技",
    "receiver_name":"Example SG Pte. Ltd.",
    "receiver_country":"Singapore",
    "transfer_purpose":"客户管理",
    "pii_count":200000,
    "spi_count":800,
    "has_scc_draft":false,
    "uploaded_files":[]
  }'
```
