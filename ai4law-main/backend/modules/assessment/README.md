# Assessment Module

## Purpose
Generate v0 security assessment report with traceable intermediate structures.

## Endpoint
- `POST /api/v1/assessment/generate`
- `POST /api/v1/assessment/generate_async`
- `GET /api/v1/assessment/tasks/{task_id}`
- `POST /api/v1/assessment/tasks/{task_id}/retry`

输出：
- `report_path`：docx 文件路径
- `output_files.markdown`：md 文件路径

路径校验：
- 默认会先做诊断路径匹配；若未命中安全评估路径，请求会返回 400。
- 需要强制生成时可传 `force_override_path=true`（报告会保留路径不匹配告警）。

## Example
```bash
curl -X POST http://127.0.0.1:8000/api/v1/assessment/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "company_name":"示例科技",
    "industry":"电商",
    "is_ciio":false,
    "contains_important_data":false,
    "pii_count":320000,
    "spi_count":800,
    "transfer_purpose":"集团统一客户管理",
    "receiver_country":"新加坡",
    "force_override_path": true,
    "uploaded_files":[]
  }'
```
