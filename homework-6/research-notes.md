# Research Notes — context7 queries (Task 2 / Task 4)

These are the **MCP context7** lookups made during code generation of the multi-agent banking
pipeline. Each entry records what was searched, the library ID context7 returned, and the concrete
pattern applied in the code.

> Tooling: context7 via the `everything-claude-code` MCP server (`resolve-library-id` →
> `query-docs`), configured in `mcp.json`.

---

## Query 1 — Decimal / monetary arithmetic

- **Search:** "Python decimal module: parse string amounts, quantize to two decimal places with
  `ROUND_HALF_UP`, avoid float, getcontext precision"
- **context7 library ID:** `/python/cpython/v3.11.14` (Doc/library/decimal.rst)
- **Key insight applied:**
  - Construct amounts directly from the JSON **string** field — `Decimal("1500.00")` — which
    "retains full input precision," instead of going through `float` (which introduces binary drift).
  - Round money with `Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`. The docs
    confirm rounding happens on the **result** of `quantize`, and `Decimal('10') ** -2` /
    `Decimal('.01')` is the canonical two-places exponent.
  - Applied in `agents/_shared.py::to_money()` and in fraud/compliance amount comparisons so every
    monetary value is a normalized 2-dp `Decimal`.

## Query 2 — Timezone-aware ISO-8601 datetimes

- **Search:** "datetime: parse ISO 8601 string with `Z` suffix using `fromisoformat`, create
  timezone-aware UTC now, format back to ISO 8601"
- **context7 library ID:** `/python/cpython/v3.11.14` (Doc/library/datetime.rst)
- **Key insight applied:**
  - Python **3.11** `datetime.fromisoformat()` accepts the `Z` suffix and offsets directly
    (`...01Z` → `tzinfo=timezone.utc`), so the sample timestamps (`2026-03-16T09:00:00Z`) parse
    without manual `Z`→`+00:00` substitution.
  - Generate message timestamps with `datetime.now(timezone.utc).isoformat()` (always tz-aware —
    docs warn naive datetimes are unsafe) and read the transaction hour from the parsed,
    UTC-normalized datetime for the fraud "off-hours" rule.
  - Applied in `agents/_shared.py::utc_now_iso()` and `fraud_detector.py` off-hours detection.

## Query 3 — FastMCP server (Task 4)

- **Search:** "Define tools with `@mcp.tool` and a resource template with `@mcp.resource`, run
  server over stdio, FastMCP v3 minimal server"
- **context7 library ID:** `/prefecthq/fastmcp` (v3.x)
- **Key insight applied:**
  - `@mcp.tool` decorates plain typed functions (auto schema from signature); `@mcp.resource("uri")`
    exposes read-only data; `mcp.run()` uses **STDIO transport by default** — exactly what the
    `mcp.json` `pipeline-status` server needs.
  - Applied in `mcp/server.py` for `get_transaction_status`, `list_pipeline_results`, and the
    `pipeline://summary` resource.
