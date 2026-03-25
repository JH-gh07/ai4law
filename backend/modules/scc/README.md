# SCC Module

## Purpose
Generate PIPIA report for SCC/certification route.

## Endpoint
- `POST /api/v1/scc/generate`

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
