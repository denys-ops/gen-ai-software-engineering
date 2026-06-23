"""REST API gateway — wraps the file-based banking pipeline behind HTTP endpoints.

Submit transactions and retrieve results via API calls instead of running integrator.py by hand.
Processing is synchronous and inline: POST /transactions runs the pipeline for each submitted
transaction and returns the result. Reads (summary, by-id, rules, config) expose pipeline state.

Run:  uv run uvicorn api.main:app --port 8000      (then open http://localhost:8000/docs)

Concurrency: the underlying file-move pipeline is single-writer by design, and FastAPI runs sync
endpoints in a threadpool, so all pipeline mutations are serialized behind a module-level lock.
Run uvicorn single-worker (the default) — do not pass --workers > 1.
"""

import json
import threading
from pathlib import Path
from typing import Any, Union

from fastapi import Body, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict

import config
import integrator

# Resolve shared/ relative to this package so the gateway works from any cwd.
ROOT = Path(__file__).resolve().parent.parent
SHARED_DIR = str(ROOT / "shared")
RESULTS_DIR = ROOT / "shared" / "results"

# Serializes every pipeline mutation + summary rebuild (single-writer invariant).
_pipeline_lock = threading.Lock()

# PII-safe projection (no account numbers, names, or descriptions) — mirrors mcp/server.py.
_PUBLIC_FIELDS = (
    "transaction_id",
    "status",
    "reason",
    "risk_score",
    "triggered_rules",
    "flagged",
    "decision",
    "decision_reason",
    "notifications",
)

app = FastAPI(
    title="Banking Pipeline Gateway",
    description="HTTP gateway over the multi-agent banking transaction pipeline.",
    version="1.0.0",
)


class TransactionIn(BaseModel):
    """Inbound transaction. The transaction_validator agent performs the real validation;
    this model documents the shape for Swagger and allows extra/metadata fields through."""

    model_config = ConfigDict(extra="allow")

    transaction_id: str
    timestamp: str
    source_account: str
    destination_account: str
    amount: Union[str, float, int]
    currency: str
    transaction_type: str
    description: Union[str, None] = None
    metadata: Union[dict, None] = None


def _public_view(data: dict[str, Any]) -> dict[str, Any]:
    return {k: data.get(k) for k in _PUBLIC_FIELDS if k in data}


def _resolve_stages_or_400(stages: Union[str, None]):
    if stages is None:
        return None
    try:
        return config.resolve_stages(stages)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.post("/transactions")
def submit_transactions(
    payload: Union[TransactionIn, list[TransactionIn]] = Body(...),
    stages: Union[str, None] = Query(
        None,
        description="Optional CSV stage override, e.g. 'fraud_detector,notification_agent'. "
        "Unknown stage name -> 400.",
    ),
) -> list[dict[str, Any]]:
    """Submit one transaction or a batch; run the pipeline inline and return the result(s)."""
    resolved = _resolve_stages_or_400(stages)
    records = payload if isinstance(payload, list) else [payload]

    results: list[dict[str, Any]] = []
    with _pipeline_lock:
        for txn in records:
            data = integrator.process_one(
                txn.model_dump(), base_dir=SHARED_DIR, stages=resolved
            )
            results.append(_public_view(data))
        integrator.rebuild_summary(SHARED_DIR)
    return results


@app.get("/transactions")
def list_transactions() -> dict[str, Any]:
    """List every processed transaction from the freshly rebuilt summary."""
    with _pipeline_lock:
        summary = integrator.rebuild_summary(SHARED_DIR)
    return {"count": summary["counts"]["total"], "transactions": summary["transactions"]}


@app.get("/transactions/{txn_id}")
def get_transaction(txn_id: str) -> dict[str, Any]:
    """Return the pipeline result for a single transaction id (PII-safe view)."""
    result_file = RESULTS_DIR / f"{txn_id}.json"
    if not result_file.exists():
        raise HTTPException(
            status_code=404, detail=f"no result for transaction_id {txn_id!r}"
        )
    message = json.loads(result_file.read_text(encoding="utf-8"))
    return {"found": True, **_public_view(message.get("data", {}))}


@app.get("/summary")
def summary() -> dict[str, Any]:
    """Aggregate counts + per-transaction summary of the latest pipeline state."""
    with _pipeline_lock:
        return integrator.rebuild_summary(SHARED_DIR)


@app.get("/rules")
def rules() -> dict[str, Any]:
    """Return the active notification rule set (demonstrates the configurable rule engine)."""
    from agents import rule_engine

    return {"path": config.RULES_PATH, "rules": rule_engine.load_rules()}


@app.get("/config")
def pipeline_config() -> dict[str, Any]:
    """Return the active pipeline configuration (demonstrates the flexible/toggleable pipeline)."""
    return {
        "enabled_stages": list(config.ENABLED_STAGES),
        "default_stages": list(config.DEFAULT_STAGES),
        "thresholds": {
            "high_value_threshold": str(config.HIGH_VALUE_THRESHOLD),
            "fraud_flag_threshold": config.FRAUD_FLAG_THRESHOLD,
            "off_hours": [config.OFF_HOURS_START, config.OFF_HOURS_END],
            "home_country": config.HOME_COUNTRY,
            "weights": {
                "high_value": config.WEIGHT_HIGH_VALUE,
                "cross_border": config.WEIGHT_CROSS_BORDER,
                "off_hours": config.WEIGHT_OFF_HOURS,
            },
            "sanctioned_countries": sorted(config.SANCTIONED_COUNTRIES),
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
