"""Custom FastMCP server — makes the banking pipeline queryable.

Exposes:
  - tool  get_transaction_status(transaction_id) -> current status from shared/results/
  - tool  list_pipeline_results()                -> summary of all processed transactions
  - resource pipeline://summary                  -> latest pipeline run summary as text

Run standalone:  uv run python mcp/server.py   (STDIO transport by default)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# Resolve shared/results relative to this file so the server works from any cwd.
RESULTS_DIR = Path(__file__).resolve().parent.parent / "shared" / "results"
SUMMARY_FILE = RESULTS_DIR / "summary.json"

mcp = FastMCP("pipeline-status")

# Fields safe to surface (no PII such as account numbers, names, or descriptions).
_PUBLIC_FIELDS = (
    "transaction_id",
    "status",
    "reason",
    "risk_score",
    "triggered_rules",
    "flagged",
    "decision",
    "decision_reason",
)


def _public_view(data: dict[str, Any]) -> dict[str, Any]:
    return {k: data.get(k) for k in _PUBLIC_FIELDS if k in data}


def _load_summary() -> dict[str, Any] | None:
    if not SUMMARY_FILE.exists():
        return None
    return json.loads(SUMMARY_FILE.read_text(encoding="utf-8"))


@mcp.tool
def get_transaction_status(transaction_id: str) -> dict[str, Any]:
    """Return the current pipeline status for a single transaction.

    Reads shared/results/<transaction_id>.json. Returns an ``error`` field if the pipeline
    has not produced a result for that id (run the pipeline first).
    """
    result_file = RESULTS_DIR / f"{transaction_id}.json"
    if not result_file.exists():
        return {
            "transaction_id": transaction_id,
            "found": False,
            "error": "no result for this transaction_id (has the pipeline run?)",
        }
    message = json.loads(result_file.read_text(encoding="utf-8"))
    return {"found": True, **_public_view(message.get("data", {}))}


@mcp.tool
def list_pipeline_results() -> dict[str, Any]:
    """Return a summary of all processed transactions from the latest pipeline run."""
    summary = _load_summary()
    if summary is None:
        return {"error": "no pipeline run found (run integrator.py first)", "counts": {}, "transactions": []}
    return {
        "generated_at": summary.get("generated_at"),
        "counts": summary.get("counts", {}),
        "transactions": summary.get("transactions", []),
    }


@mcp.resource("pipeline://summary")
def pipeline_summary() -> str:
    """Latest pipeline run summary as human-readable text."""
    summary = _load_summary()
    if summary is None:
        return "No pipeline run found. Run `python integrator.py` to generate results."

    counts = summary.get("counts", {})
    lines = [
        f"Pipeline summary (generated {summary.get('generated_at', 'n/a')})",
        (
            f"total={counts.get('total', 0)} validated={counts.get('validated', 0)} "
            f"rejected={counts.get('rejected', 0)} flagged={counts.get('flagged', 0)} "
            f"approved={counts.get('approved', 0)} held={counts.get('held', 0)}"
        ),
        "",
    ]
    for txn in summary.get("transactions", []):
        reason = txn.get("decision_reason") or txn.get("reason") or "-"
        lines.append(
            f"{txn.get('transaction_id')}: status={txn.get('status')} "
            f"risk={txn.get('risk_score')} decision={txn.get('decision') or '-'} ({reason})"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
