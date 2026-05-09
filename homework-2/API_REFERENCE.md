# API Reference — Support Tickets API

**Base URL:** `http://localhost:3000`  
**Interactive docs:** `http://localhost:3000/docs` (Swagger UI with try-it-out)  
**OpenAPI schema:** `http://localhost:3000/openapi.json`

---

## Error Response Format

All 4xx responses follow this envelope:

```json
{
  "error": "<short human-readable message>",
  "details": [{"field": "<field name>", "message": "<text>"}]
}
```

FastAPI's 422 validation errors are intercepted and converted to 400 with this same shape.

---

## Ticket Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto | Auto-generated on creation |
| `customer_id` | string | Yes | Customer identifier |
| `customer_email` | string | Yes | Validated email address |
| `customer_name` | string | Yes | Display name |
| `subject` | string | Yes | 1–200 characters |
| `description` | string | Yes | 10–2000 characters |
| `category` | string | No | `account_access`, `technical_issue`, `billing_question`, `feature_request`, `bug_report`, `other` |
| `priority` | string | No | `urgent`, `high`, `medium`, `low` |
| `status` | string | No | `new`, `in_progress`, `waiting_customer`, `resolved`, `closed` (default: `new`) |
| `assigned_to` | string | No | Assigned agent/team (default: `null`) |
| `tags` | array | No | String labels (default: `[]`) |
| `metadata` | object | No | `{source, browser, device_type}` (default: `null`) |
| `created_at` | ISO 8601 | Auto | UTC creation timestamp |
| `updated_at` | ISO 8601 | Auto | UTC last-modification timestamp |
| `resolved_at` | ISO 8601 | Auto | Set when `status → resolved`; cleared on reopen |

**TicketMetadata:** `source` (`web_form`, `email`, `api`, `chat`, `phone`), `browser` (free text), `device_type` (`desktop`, `mobile`, `tablet`).

---

## Endpoint Summary

| Method | Path | Success | Description |
|--------|------|---------|-------------|
| POST | `/tickets` | 201 | Create ticket; `?auto_classify=true` runs classifier |
| GET | `/tickets` | 200 | List all; `?category=`, `?priority=`, `?status=` filters |
| GET | `/tickets/{id}` | 200 | Get by UUID |
| PUT | `/tickets/{id}` | 200 | Partial update (omitted fields unchanged; `null` clears) |
| DELETE | `/tickets/{id}` | 204 | Delete |
| POST | `/tickets/import` | 200 | Bulk import CSV/JSON/XML; `?format=` optional |
| POST | `/tickets/{id}/auto-classify` | 200 | Run classifier, update ticket, return `ClassificationResult` |
| GET | `/tickets/{id}/classifications` | 200 | Retrieve classification audit log |

---

## Quick Examples

```bash
# Create a ticket
curl -s -X POST http://localhost:3000/tickets \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"CUST-1","customer_email":"a@b.com","customer_name":"Alice",
       "subject":"Cannot log in","description":"Login fails since this morning."}' \
  | python3 -m json.tool

# List tickets (with filters)
curl -s 'http://localhost:3000/tickets?status=new&priority=high' | python3 -m json.tool

# Import from CSV
curl -s -X POST http://localhost:3000/tickets/import \
  -F "file=@demo/sample_tickets.csv" | python3 -m json.tool

# Auto-classify
curl -s -X POST http://localhost:3000/tickets/<uuid>/auto-classify | python3 -m json.tool
```

---

## Auto-Classification — Overview

The classifier is a pure rule-based keyword matcher. It assigns `category` and `priority` based on `subject + description` content. Confidence is `min(1.0, distinct_keyword_hits / 5.0)` rounded to 2 decimals.

**ClassificationResult:**

```json
{"ticket_id": "...", "category": "account_access", "priority": "urgent",
 "confidence": 0.60, "reasoning": "Matched priority keywords: ['critical']...",
 "keywords_found": ["critical", "login", "access"]}
```

---

## Further Reading

| Resource | When to use it |
|----------|---------------|
| [`docs/details/api/endpoints.md`](./docs/details/api/endpoints.md) | Full per-endpoint request/response schemas, all error codes, complete cURL examples |
| [`docs/details/api/error-catalog.md`](./docs/details/api/error-catalog.md) | All 18 validation error conditions; keyword classification tables (priority + category) |
| [`docs/details/api/examples.md`](./docs/details/api/examples.md) | CSV/JSON/XML file format specifications with annotated examples |
| `http://localhost:3000/docs` | Interactive try-it-out (Swagger UI) |
