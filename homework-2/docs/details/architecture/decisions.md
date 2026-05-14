# Design Decisions, Trade-offs, Security and Performance

## In-Memory Store

**Decision:** Python dict keyed by UUID; no persistent storage.

**Chosen for:** Simplicity (no DB setup), test isolation (fresh instance per test via `dependency_overrides`), and spec compliance (spec requires in-memory demo).

**Trade-off:** Data lost on restart. Production would use PostgreSQL or similar.

## Rule-Based Classifier vs. LLM

**Decision:** Static keyword tables and substring matching; no LLM API calls.

**Chosen for:** Determinism (identical output for identical input), zero cost, trivial testability, and sub-5ms latency per call.

**Trade-off:** Limited semantic understanding. False positives (e.g., "$500 transaction fee" matches `technical_issue` via "500") and false negatives (phrasing mismatches) are accepted imprecision for a demo. Production would use an LLM with caching or fine-tuned embeddings.

## First-Match Category Precedence

**Decision:** Return the first category (in declaration order) whose keywords appear in the text.

**Chosen for:** Single-pass matching, unambiguous results, and determinism. Table order is the single source of truth for precedence.

**Trade-off:** Reordering the keyword table changes results. Acceptable because the table order is locked by the spec.

## Confidence as Keyword-Count Proxy

**Decision:** `min(1.0, distinct_hits / 5.0)`.

**Chosen for:** Simplicity, interpretability, and no ML model required.

**Limitation:** Does not reflect semantic relevance — five generic keyword hits ≠ high semantic confidence. Acceptable for a demo.

## defusedxml for XML Parsing

**Decision:** Use `defusedxml.ElementTree` instead of stdlib `xml.etree.ElementTree`.

**Chosen for:** Prevents XXE (XML External Entity) injection and billion-laughs attacks. Same API as stdlib; no performance penalty for well-formed XML. Recommended by OWASP.

---

## Security Considerations

### XML Parsing
Threat: XXE injection and billion-laughs DoS.  
Mitigation: `defusedxml.ElementTree` disables external entity resolution.

### Email Validation
`customer_email` uses Pydantic's `EmailStr` (RFC 5322 subset). Does not verify deliverability — by design (spec prohibits network I/O).

### Extra Field Rejection
`TicketCreate` and `TicketUpdate` use `extra="forbid"`, rejecting unknown fields and preventing injection of arbitrary data.

### File Uploads
`/tickets/import` has no file size limit (spec intentionally omits size validation). A multi-gigabyte file will be read entirely into memory. Production systems should enforce size limits at the load-balancer level.

---

## Performance Considerations

### Classifier
O(text_length × keyword_count) per call. ~30 keywords; typical ticket text 100–2000 characters. Measured: **< 1 ms** per classification.

### Store Filtering
O(n) linear scan per filter. Acceptable for < 10,000 tickets in a demo. Production uses database indices.

### Bulk Import
All rows parsed and validated in memory before any are inserted. O(file_size) parsing + O(rows × fields) validation. Acceptable for files up to ~1 GB on an 8 GB machine. Streaming parsers would reduce peak memory but complicate error reporting.

**Measured benchmarks (see `TESTING_GUIDE.md`):**

| Operation | Threshold | Actual | Margin |
|-----------|-----------|--------|--------|
| Import 50-row CSV | < 500 ms | 28.7 ms | 17× |
| List 1000 tickets | < 200 ms | 17.7 ms | 11× |
| Classify single ticket | < 50 ms | 2.9 ms | 17× |
| 20 concurrent creates | < 2 s | 46.2 ms | 43× |
| Import 30-row XML | < 750 ms | 14.5 ms | 52× |
