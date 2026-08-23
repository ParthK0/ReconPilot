# 05 — API Specification
## ReconPilot (FastAPI, REST, JSON)

Base path: `/api/v1`

## 1. Authentication

For the Buildathon build, a single static bearer token is enough — this is a demo system processing synthetic data, not a production multi-tenant service, so full OAuth2/JWT would spend build time a panel isn't scoring.

```
Authorization: Bearer <DEMO_API_KEY>
```

Document this as a known simplification in the repo README, with a one-line note on what production auth would add (per-user OAuth2, scoped to a real Razorpay merchant account).

## 2. Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/batches` | Upload 3 CSVs, create a batch |
| GET | `/batches/{batch_id}` | Batch status |
| POST | `/batches/{batch_id}/process` | Trigger the pipeline (or auto-triggered on upload) |
| GET | `/batches/{batch_id}/matches` | Paginated match list |
| GET | `/matches/{match_id}` | Single match detail + AI evidence |
| GET | `/batches/{batch_id}/exceptions` | Grouped exception report |
| GET | `/batches/{batch_id}/metrics` | Dashboard numbers |
| POST | `/matches/{match_id}/review` | Human marks a match reviewed/resolved |
| GET | `/batches/{batch_id}/export` | Export final report (CSV) |

No forecast endpoint — cash position forecasting is a frozen-out future enhancement (01-PRD.md §7), not attempted in this build, so it isn't specified here either.

## 3. Endpoint Detail

### `POST /batches`
Multipart upload.

**Request:** `multipart/form-data` — `settlement_csv`, `bank_csv`, `invoice_csv`

**Response `201`:**
```json
{
  "batch_id": "b1a2c3d4-...",
  "status": "processing",
  "uploaded_at": "2026-08-21T10:00:00Z"
}
```

**Errors:** `400` missing a file, `422` a file doesn't match the expected column schema.

### `GET /batches/{batch_id}`
**Response `200`:**
```json
{
  "batch_id": "b1a2c3d4-...",
  "status": "done",
  "records_processed": 100
}
```
**Errors:** `404` unknown batch_id.

### `GET /batches/{batch_id}/matches`
Query params: `status` (matched|exception), `page`, `page_size`.

**Response `200`:**
```json
{
  "page": 1,
  "page_size": 25,
  "total": 100,
  "matches": [
    {
      "match_id": "m1",
      "status": "matched",
      "match_method": "ai",
      "confidence": 99.0,
      "settlement_record_id": "r2",
      "invoice_record_id": "r1"
    }
  ]
}
```

### `GET /matches/{match_id}`
**Response `200`:**
```json
{
  "match_id": "m1",
  "status": "matched",
  "match_method": "ai",
  "confidence": 99.0,
  "records": { "settlement": {"...": "..."}, "invoice": {"...": "..."} },
  "ai_verification": {
    "difference_amount": 30.00,
    "likely_reason": "processing_fee",
    "reasoning_explanation": "The ₹30 gap equals the settlement's recorded processing fee exactly.",
    "expected_value": 11970.00,
    "ai_confidence": 98.0,
    "adjusted_confidence": 99.0,
    "evidence_field": "settlement.fees",
    "model_used": "gpt-5.6-terra"
  }
}
```
**Errors:** `404` unknown match_id.

### `GET /batches/{batch_id}/exceptions`
**Response `200`:**
```json
{
  "settlement_delay": 5,
  "missing_credit": 3,
  "duplicate_invoice": 2,
  "refund_pending": 1,
  "unknown": 1,
  "items": [
    {"record_id": "r9", "category": "unknown", "notes": "no candidate within date window"}
  ]
}
```

### `GET /batches/{batch_id}/metrics`
**Response `200`:**
```json
{
  "records_processed": 100,
  "rule_matches": 91,
  "ai_verified": 7,
  "needs_review": 2,
  "match_rate": 98.0,
  "precision": 99.0,
  "processing_time_seconds": 14.8,
  "manual_hours_saved": 4.5
}
```

### `POST /matches/{match_id}/review`
**Request:**
```json
{ "resolved": true, "reviewer_note": "confirmed manually against bank portal" }
```
**Response `200`:** the updated match object.

### `GET /batches/{batch_id}/export`
Returns `text/csv` — one row per record, with status, confidence, evidence, and reviewer-action columns.

## 4. Error Codes

| Code | Meaning | ReconPilot-specific behavior |
|---|---|---|
| 400 | Bad request | Missing file, malformed multipart |
| 401 | Unauthorized | Missing/invalid bearer token |
| 404 | Not found | Unknown batch_id / match_id |
| 422 | Validation error | CSV columns don't match the expected schema |
| 429 | Rate limited | The LLM provider rate-limited a call — the affected record is marked `needs_review`, the batch still completes |
| 500 | Internal error | Unhandled server error |
| 503 | AI provider unavailable | Same graceful-degradation behavior as 429 — never fails the whole batch |
