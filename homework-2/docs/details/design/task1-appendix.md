# Task 1 Design — Detailed Appendix

## Route Contracts (Full Detail)

### POST `/tickets` — create

Request body: `TicketCreate`. `extra="forbid"` set.

Server-side population:
- `id` = `UUID4`, `created_at` = `updated_at` = current UTC. `resolved_at = null` unless initial `status="resolved"`.

Errors: 400 for any model-validation failure.

### GET `/tickets` — list with filters

Query parameters (optional, single-valued): `category`, `priority`, `status` (must be valid enum values).  
Filters compose with AND. Empty result → `200 []`, never `404`. No pagination.

### GET `/tickets/{ticket_id}` — fetch by ID

`ticket_id` typed as UUID. Errors: 400 (bad UUID), 404 (not found).

### PUT `/tickets/{ticket_id}` — partial update

Uses `payload.model_dump(exclude_unset=True)` — only keys present in the body are applied.  
Explicit `null` clears the field; absent key retains current value. `updated_at` always refreshed.

Status side effects on `resolved_at`:

| Previous status | New status | Effect |
|-----------------|------------|--------|
| not `resolved` | `resolved` | `resolved_at = utcnow()` |
| `resolved` | not `resolved` | `resolved_at = None` |
| any | absent | unchanged |

Immutable fields: `id`, `customer_id`, `customer_email`, `customer_name`, `created_at` — rejected via `extra="forbid"`.

### DELETE `/tickets/{ticket_id}` — delete

204 on success. Second DELETE on same ID → 404.

---

## Import Endpoint Contract

### Wire Format

`Content-Type: multipart/form-data`. Field `file` (UploadFile). Optional query param `format` (`csv|json|xml`).

### Format Detection Priority

1. Explicit `?format=` query param.
2. `UploadFile.content_type` MIME mapping.
3. Filename suffix (case-insensitive).

All three fail → 400, `field: "format"`.

### Pipeline

```
UploadFile bytes → parse_<format>(bytes) → (list[TicketCreate], list[ImportError])
  → for each TicketCreate: store.insert(Ticket)
  → assemble ImportSummary
```

### Edge Cases

| Situation | HTTP | Field |
|-----------|------|-------|
| No `file` field | 400 | `file` |
| Empty file (0 bytes) | 400 | `file` |
| Unrecognised format | 400 | `format` |
| Container-level malformed | 400 | `file` |
| Some rows valid, some invalid | 200 | per-row in `ImportSummary.errors` |
| All rows invalid | 200 | `successful = 0` |
| File too large | **no limit** | n/a |

---

## XML Schema

Root element: `<tickets>`, child `<ticket>`. Snake_case child elements. `<tags><tag>` wrapper. `<metadata>` wrapper. All values as element text content (no attributes). Whitespace stripped. Parsed with `defusedxml.ElementTree` exclusively.

---

## CSV Format

UTF-8, RFC 4180. Required header row. Required headers: `customer_id`, `customer_email`, `customer_name`, `subject`, `description`. Optional headers: `category`, `priority`, `status`, `assigned_to`, `tags`, `metadata_source`, `metadata_browser`, `metadata_device_type`. Unknown headers → 400. Blank cell = field omitted. `tags` semicolon-separated.

---

## Validation Error Catalogue

| # | Situation | `details[].field` | HTTP |
|---|-----------|-------------------|------|
| 1 | Missing required field | field name | 400 |
| 2 | Invalid `category` | `category` | 400 |
| 3 | Invalid `priority` | `priority` | 400 |
| 4 | Invalid `status` | `status` | 400 |
| 5 | Invalid `metadata.source` | `metadata.source` | 400 |
| 6 | Invalid `metadata.device_type` | `metadata.device_type` | 400 |
| 7 | Invalid email | `customer_email` | 400 |
| 8 | `subject` out of 1–200 range | `subject` | 400 |
| 9 | `description` out of 10–2000 range | `description` | 400 |
| 10 | Unknown extra field | field name | 400 |
| 11 | `tags` not a list | `tags` | 400 |
| 12 | `metadata` not an object | `metadata` | 400 |
| 13 | `ticket_id` not a UUID | `ticket_id` | 400 |
| 14 | `ticket_id` valid but not found | `ticket_id` | 404 |
| 15 | Import: missing `file` | `file` | 400 |
| 16 | Import: empty file | `file` | 400 |
| 17 | Import: cannot detect format | `format` | 400 |
| 18 | Import: container-level malformed | `file` | 400 |
