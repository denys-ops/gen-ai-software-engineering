# Manual Testing Checklist

Use this checklist to verify core workflows manually via `curl`, Postman, or the interactive demo script.

**Setup (once per session):**

```bash
cd homework-2
PYTHONPATH=src uv run uvicorn app.main:app --port 3000 --reload &
```

**Swagger UI validation:**
- [ ] Open `http://localhost:3000/docs`
- [ ] All endpoints present: `/tickets` (POST/GET), `/tickets/{id}` (GET/PUT/DELETE), `/tickets/{id}/auto-classify` (POST), `/tickets/import` (POST)
- [ ] Request/response schemas match `API_REFERENCE.md`

**Create endpoint:**
- [ ] POST with valid JSON → **201** + ticket with UUID `id`
- [ ] POST missing required field (`customer_email`) → **400** + error envelope
- [ ] POST with invalid email → **400** + email validation error
- [ ] POST with `subject` < 1 char or > 200 chars → **400**
- [ ] POST with `description` < 10 or > 2000 chars → **400**
- [ ] POST with invalid `category`, `priority`, or `status` → **400**
- [ ] POST with unknown extra field → **400**
- [ ] POST with `auto_classify=true` → **201** + `category`/`priority` assigned by classifier

**List endpoint:**
- [ ] GET `/tickets` → **200** + `[]` initially
- [ ] POST 3 tickets with different categories → GET `/tickets` → **200** + array length 3
- [ ] GET `/tickets?status=new` → filtered by status
- [ ] GET `/tickets?category=technical_issue` → filtered by category
- [ ] GET `/tickets?priority=urgent` → filtered by priority
- [ ] GET `/tickets?category=billing_question&priority=high` → combined filter (AND)
- [ ] GET `/tickets?status=invalid_status` → **400**

**Get single ticket:**
- [ ] POST a ticket, capture UUID → GET `/tickets/{uuid}` → **200** + exact ticket JSON
- [ ] GET `/tickets/not-a-uuid` → **400**
- [ ] GET `/tickets/00000000-0000-0000-0000-000000000000` (valid UUID, not found) → **404**

**Update endpoint:**
- [ ] POST ticket → PUT `/tickets/{uuid}` with `{"status": "in_progress"}` → **200**, other fields unchanged
- [ ] PUT with `{"status": "resolved"}` → **200** + `resolved_at` set
- [ ] PUT with `{"status": "new"}` after resolved → **200** + `resolved_at` cleared
- [ ] PUT with invalid enum → **400**
- [ ] PUT on non-existent ticket → **404**

**Delete endpoint:**
- [ ] POST ticket → DELETE `/tickets/{uuid}` → **204** (no body)
- [ ] GET `/tickets/{uuid}` after delete → **404**
- [ ] DELETE same UUID again → **404**

**CSV import:**
- [ ] POST `/tickets/import` with `demo/sample_tickets.csv` → **200** + `{"total": 50, "successful": 50}`
- [ ] POST with `tests/fixtures/invalid_tickets.csv` → **200** + errors in ImportSummary
- [ ] POST with empty CSV (headers only) → **400**
- [ ] POST with `.csv` filename (no `format=`) → auto-detect CSV

**JSON import:**
- [ ] POST `/tickets/import` with `demo/sample_tickets.json` → **200** + `{"total": 20, "successful": 20}`
- [ ] POST with `tests/fixtures/invalid_tickets.json` → **200** + errors
- [ ] POST with `[]` (empty array) → **200** + `{"total": 0, "successful": 0}`

**XML import:**
- [ ] POST `/tickets/import` with `demo/sample_tickets.xml` → **200** + `{"total": 30, "successful": 30}`
- [ ] POST with `tests/fixtures/malformed.xml` → **400**

**Auto-classify endpoint:**
- [ ] POST ticket with description containing `"can't access"` → POST `/auto-classify` → **200** + `category=account_access`, `priority=urgent`
- [ ] POST `/tickets/{uuid}/auto-classify` with vague description → **200** + lower confidence
- [ ] POST auto-classify on non-existent ticket → **404**

**Classification log:**
- [ ] POST ticket with `auto_classify=true` → GET `/tickets/{uuid}/classifications` → **200** + array with 1 entry
- [ ] POST auto-classify multiple times → each call appended; GET returns all entries

**Concurrent stress:**
- [ ] Send 20 concurrent POST requests to `/tickets` → all complete < 2 seconds; all 20 queryable via GET

**Cleanup:**

```bash
pkill -f "uvicorn app.main:app"
```
