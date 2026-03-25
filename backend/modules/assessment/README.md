# Assessment Module

## Purpose
Generate v0 security assessment report with traceable intermediate structures.

## Endpoint
- `POST /api/v1/assessment/generate`

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
    "uploaded_files":[]
  }'
```
