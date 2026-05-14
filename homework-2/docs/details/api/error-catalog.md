# Error Catalog

## Validation Error Conditions

All 4xx responses use this envelope:

```json
{"error": "<short message>", "details": [{"field": "<name>", "message": "<text>"}]}
```

| # | Situation | Endpoint(s) | `details[].field` | HTTP |
|---|-----------|-------------|-------------------|------|
| 1 | Missing required field on POST | POST `/tickets` | field name | 400 |
| 2 | Invalid `category` value | POST, PUT, GET (query) | `category` | 400 |
| 3 | Invalid `priority` value | POST, PUT, GET (query) | `priority` | 400 |
| 4 | Invalid `status` value | POST, PUT, GET (query) | `status` | 400 |
| 5 | Invalid `metadata.source` | POST, PUT | `metadata.source` | 400 |
| 6 | Invalid `metadata.device_type` | POST, PUT | `metadata.device_type` | 400 |
| 7 | `customer_email` not valid email | POST | `customer_email` | 400 |
| 8 | `subject` < 1 or > 200 chars | POST, PUT | `subject` | 400 |
| 9 | `description` < 10 or > 2000 chars | POST, PUT | `description` | 400 |
| 10 | Unknown extra field in body | POST, PUT | the unknown field name | 400 |
| 11 | `tags` not a list | POST, PUT | `tags` | 400 |
| 12 | `metadata` not an object | POST, PUT | `metadata` | 400 |
| 13 | `ticket_id` path not a UUID | GET, PUT, DELETE | `ticket_id` | 400 |
| 14 | `ticket_id` valid UUID but not found | GET, PUT, DELETE | `ticket_id` | 404 |
| 15 | Import: missing `file` field | POST `/tickets/import` | `file` | 400 |
| 16 | Import: empty file | POST `/tickets/import` | `file` | 400 |
| 17 | Import: cannot detect format | POST `/tickets/import` | `format` | 400 |
| 18 | Import: container-level malformed file | POST `/tickets/import` | `file` | 400 |

---

## Classification Keyword Tables

### Priority Keywords

Priority is resolved by precedence: `urgent > high > low > medium` (medium is the default; never in `keywords_found`).

| Priority | Keywords |
|----------|----------|
| `urgent` | `"can't access"`, `"critical"`, `"production down"`, `"security"` |
| `high` | `"important"`, `"blocking"`, `"asap"` |
| `low` | `"minor"`, `"cosmetic"`, `"suggestion"` |
| `medium` | (default — no keywords) |

### Category Keywords

Category is resolved by first-match in declaration order. `other` is the fallback (never in `keywords_found`).

| Category | Keywords |
|----------|----------|
| `account_access` | `"login"`, `"password"`, `"2fa"`, `"account"`, `"access"`, `"sign in"`, `"locked out"` |
| `technical_issue` | `"bug"`, `"error"`, `"crash"`, `"broken"`, `"not working"`, `"exception"`, `"500"` |
| `billing_question` | `"payment"`, `"invoice"`, `"refund"`, `"charge"`, `"billing"`, `"subscription"` |
| `feature_request` | `"feature"`, `"enhancement"`, `"request"`, `"would like"`, `"suggestion"`, `"add"` |
| `bug_report` | `"defect"`, `"reproduce"`, `"steps to reproduce"`, `"regression"`, `"expected behavior"` |
| `other` | (default — no keywords) |

### Confidence Formula

```
keywords_found = unique matched priority keywords + unique matched category keywords (priority-first order)
confidence = round(min(1.0, len(keywords_found) / 5.0), 2)
```

Examples: 0 hits → 0.00, 1 hit → 0.20, 5+ hits → 1.00.

### Matching Rules

- Substring matching via `in` (no tokenisation, no stemming).
- Case-insensitive: text is lowercased before matching.
- `keywords_found` is deduplicated; priority keywords listed first.
- Priority: first matching level in precedence order wins.
- Category: first-listed matching category wins.

### Cross-Table Notes

- `"suggestion"` appears in both `low` (priority) and `feature_request` (category); counted once in `keywords_found`.
- `"can't access"` (urgent) and `"access"` (account_access) both match text containing "can't access"; both counted.
- `"500"` is a substring that may match numeric content (e.g., "$500") — accepted imprecision per spec.
