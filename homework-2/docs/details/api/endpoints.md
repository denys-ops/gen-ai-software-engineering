# API Endpoints — Full Reference

**Base URL:** `http://localhost:3000`  
**Interactive docs:** `http://localhost:3000/docs` (Swagger UI)

---

## POST /tickets

Create a new support ticket, optionally with auto-classification.

**Request body — TicketCreate**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `customer_id` | string | Yes | — |
| `customer_email` | string | Yes | Valid email format |
| `customer_name` | string | Yes | — |
| `subject` | string | Yes | 1–200 characters |
| `description` | string | Yes | 10–2000 characters |
| `category` | string | No | `account_access`, `technical_issue`, `billing_question`, `feature_request`, `bug_report`, `other` |
| `priority` | string | No | `urgent`, `high`, `medium`, `low` |
| `status` | string | No | `new`, `in_progress`, `waiting_customer`, `resolved`, `closed` (defaults to `new`) |
| `assigned_to` | string | No | — |
| `tags` | array of strings | No | defaults to `[]` |
| `metadata` | object | No | `{source, browser, device_type}` — see Ticket Schema |

Unknown fields in the body are rejected with 400 (`extra="forbid"`).

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `auto_classify` | bool | `false` | If `true`, classifier overwrites `category` and `priority` after insert |

When `auto_classify=true`, any `category`/`priority` in the request body are overwritten.

**Success — 201 Created:** returns the full `Ticket` object.

**Errors**

| Code | Condition |
|------|-----------|
| 400 | Missing required field |
| 400 | Invalid email / subject length / description length |
| 400 | Invalid enum value for `category`, `priority`, `status`, or `metadata.*` |
| 400 | Unknown extra field in body |

**cURL**

```bash
curl -s -X POST http://localhost:3000/tickets \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": "CUST-1001",
    "customer_email": "alice@example.com",
    "customer_name": "Alice Example",
    "subject": "Cannot log in",
    "description": "I cannot log into my account since yesterday morning.",
    "category": "account_access",
    "priority": "high",
    "tags": ["login", "urgent"],
    "metadata": {"source": "web_form", "browser": "Chrome 120", "device_type": "desktop"}
  }' | python3 -m json.tool
```

---

## GET /tickets

List all tickets, optionally filtered. Filters compose with AND semantics.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | `account_access`, `technical_issue`, `billing_question`, `feature_request`, `bug_report`, `other` |
| `priority` | string | `urgent`, `high`, `medium`, `low` |
| `status` | string | `new`, `in_progress`, `waiting_customer`, `resolved`, `closed` |

**Success — 200 OK:** array of `Ticket` objects in insertion order. Returns `[]` when no tickets match (never 404).

**Errors**

| Code | Condition |
|------|-----------|
| 400 | Query value is not a valid enum |

**cURL**

```bash
curl -s http://localhost:3000/tickets | python3 -m json.tool
curl -s 'http://localhost:3000/tickets?status=new' | python3 -m json.tool
curl -s 'http://localhost:3000/tickets?category=account_access&priority=high' | python3 -m json.tool
```

---

## GET /tickets/{ticket_id}

Fetch a single ticket by UUID.

**Path parameters:** `ticket_id` (UUID, required)

**Success — 200 OK:** full `Ticket` object.

**Errors**

| Code | Condition |
|------|-----------|
| 400 | `ticket_id` is not a valid UUID |
| 404 | No ticket with that ID |

**cURL**

```bash
curl -s http://localhost:3000/tickets/550e8400-e29b-41d4-a716-446655440000 | python3 -m json.tool
```

---

## PUT /tickets/{ticket_id}

Partially update a ticket. Only fields present in the request body are changed. Absent fields retain current values. Explicit `null` clears the field.

**Request body — TicketUpdate (all fields optional)**

| Field | Constraints | Notes |
|-------|-------------|-------|
| `subject` | 1–200 characters | — |
| `description` | 10–2000 characters | — |
| `category` | enum or null | null clears it |
| `priority` | enum or null | null clears it |
| `status` | enum | triggers `resolved_at` side effects |
| `assigned_to` | string or null | null clears assignment |
| `tags` | array or null | null clears it |
| `metadata` | object or null | null clears it |

`id`, `customer_id`, `customer_email`, `customer_name`, `created_at` are immutable — rejected with 400 if supplied.

**Status → `resolved_at` side effects**

| Transition | Effect on `resolved_at` |
|------------|------------------------|
| any → `resolved` | set to current UTC time |
| `resolved` → any | cleared to `null` |
| status unchanged / absent | unchanged |

`updated_at` is always refreshed on every successful PUT.

**Success — 200 OK:** full updated `Ticket` object.

**Errors**

| Code | Condition |
|------|-----------|
| 400 | Invalid UUID / invalid enum / length constraint / immutable field / unknown field |
| 404 | Ticket not found |

**cURL**

```bash
# Resolve a ticket
curl -s -X PUT http://localhost:3000/tickets/550e8400-e29b-41d4-a716-446655440000 \
  -H 'Content-Type: application/json' \
  -d '{"status": "resolved"}' | python3 -m json.tool

# Update priority and assign agent
curl -s -X PUT http://localhost:3000/tickets/550e8400-e29b-41d4-a716-446655440000 \
  -H 'Content-Type: application/json' \
  -d '{"priority": "urgent", "assigned_to": "agent-5"}' | python3 -m json.tool

# Clear an optional field
curl -s -X PUT http://localhost:3000/tickets/550e8400-e29b-41d4-a716-446655440000 \
  -H 'Content-Type: application/json' \
  -d '{"assigned_to": null}' | python3 -m json.tool
```

---

## DELETE /tickets/{ticket_id}

Permanently delete a ticket by ID.

**Path parameters:** `ticket_id` (UUID, required)

**Success — 204 No Content:** empty body. A second DELETE returns 404.

**Errors**

| Code | Condition |
|------|-----------|
| 400 | `ticket_id` is not a valid UUID |
| 404 | Ticket not found |

**cURL**

```bash
curl -s -X DELETE http://localhost:3000/tickets/550e8400-e29b-41d4-a716-446655440000
```

---

## POST /tickets/import

Upload a CSV, JSON, or XML file to bulk-create tickets. Returns `ImportSummary`; partial success returns 200.

**Request:** `Content-Type: multipart/form-data`, field `file` (binary).

**Query parameter:** `format` (`csv`, `json`, or `xml`) — optional explicit override.

**Format detection (priority order)**

1. `?format=csv|json|xml` query parameter.
2. File MIME type (`text/csv`, `application/json`, `application/xml`, etc.).
3. Filename suffix (`.csv`, `.json`, `.xml`).

If none resolves, returns 400.

**Success — 200 OK**

```json
{"total": 3, "successful": 2, "failed": 1,
 "errors": [{"row": 2, "field": "customer_email", "message": "value is not a valid email address"}]}
```

Row numbers are 1-based (data rows only; CSV header is excluded).

**Errors**

| Code | Condition |
|------|-----------|
| 400 | No `file` field / empty file / undetectable format / container-level malformation |

Row-level validation failures are reported in `errors[]` within a 200 `ImportSummary`.

**cURL**

```bash
curl -s -X POST http://localhost:3000/tickets/import \
  -F "file=@demo/sample_tickets.csv" | python3 -m json.tool

curl -s -X POST 'http://localhost:3000/tickets/import?format=json' \
  -F "file=@demo/sample_tickets.json" | python3 -m json.tool

curl -s -X POST http://localhost:3000/tickets/import \
  -F "file=@demo/sample_tickets.xml" | python3 -m json.tool
```

---

## POST /tickets/{ticket_id}/auto-classify

Run the keyword-based auto-classifier on an existing ticket.

**Path parameters:** `ticket_id` (UUID, required)

**Success — 200 OK** — `ClassificationResult`:

```json
{
  "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
  "category": "account_access",
  "priority": "urgent",
  "confidence": 0.60,
  "reasoning": "Matched priority keywords: ['critical']. Matched category keywords: ['login', 'access'].",
  "keywords_found": ["critical", "login", "access"]
}
```

**ClassificationResult fields**

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | UUID | The ticket being classified |
| `category` | string | Assigned category |
| `priority` | string | Assigned priority |
| `confidence` | float | `min(1.0, distinct_hits / 5.0)` rounded to 2 decimals |
| `reasoning` | string | Human-readable explanation of matched keywords |
| `keywords_found` | array | Unique matched keywords (priority-first order) |

**Side effects:** ticket `category`, `priority`, and `updated_at` are updated; result is logged. `resolved_at` is not touched.

**Errors**

| Code | Condition |
|------|-----------|
| 400 | `ticket_id` is not a valid UUID |
| 404 | Ticket not found |

**cURL**

```bash
curl -s -X POST http://localhost:3000/tickets/550e8400-e29b-41d4-a716-446655440000/auto-classify \
  | python3 -m json.tool
```

---

## GET /tickets/{ticket_id}/classifications

Retrieve the full classification history for a ticket.

**Path parameters:** `ticket_id` (UUID, required)

**Success — 200 OK:** array of `ClassificationResult` objects in insertion order (oldest first). Returns `[]` for a ticket that has never been classified.

**Errors**

| Code | Condition |
|------|-----------|
| 400 | `ticket_id` is not a valid UUID |
| 404 | Ticket not found (even if log has entries for it) |

**cURL**

```bash
curl -s http://localhost:3000/tickets/550e8400-e29b-41d4-a716-446655440000/classifications \
  | python3 -m json.tool
```
