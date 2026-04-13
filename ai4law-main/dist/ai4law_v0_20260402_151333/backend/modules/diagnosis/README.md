# Diagnosis Module

## Purpose
Rule-based compliance path diagnosis for cross-border data transfer.

## Endpoints
- `POST /api/v1/diagnosis/evaluate`
- `POST /api/v1/diagnosis/report`

## Example
```bash
curl -X POST http://127.0.0.1:8000/api/v1/diagnosis/evaluate \
  -H 'Content-Type: application/json' \
  -d '{
    "q1_is_ciio":"no",
    "q2_has_important_data":"no",
    "q3_pii_count":200000,
    "q4_spi_count":800,
    "q5_purpose":"global crm sync"
  }'
```
