# Sample requests

The pipeline is file-based (not an HTTP API), so "requests" here are CLI invocations and MCP calls.

## CLI

```bash
# Validate only (dry-run)
uv run python agents/transaction_validator.py --dry-run

# Run the full pipeline
uv run python integrator.py

# Inspect one result
cat shared/results/TXN002.json
```

## Custom MCP server (pipeline-status)

Once registered (`claude mcp add pipeline-status -- uv run --directory homework-6 python mcp/server.py`):

| Surface | Example | Returns |
|---|---|---|
| tool `get_transaction_status` | `{"transaction_id": "TXN002"}` | status/decision/risk for that transaction |
| tool `list_pipeline_results` | `{}` | counts + per-transaction summary of the latest run |
| resource `pipeline://summary` | — | latest run summary as text |

## context7 (framework docs lookup, used during code generation)

See `../research-notes.md` for the actual queries made (FastMCP, Python `decimal`, `datetime`).
