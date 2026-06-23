"""Integrator / orchestrator for the multi-agent banking pipeline.

Sets up the shared/ directories, loads sample-transactions.json, wraps each record in a message
envelope, and runs it sequentially through the validator -> fraud_detector -> compliance_checker
agents, moving the message through input -> processing -> output between stages. Rejected
transactions short-circuit straight to results/. A summary report is written to
shared/results/summary.json.

Usage:
    python integrator.py            # uses sample-transactions.json and ./shared
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import config
from agents import (
    compliance_checker,
    fraud_detector,
    notification_agent,
    transaction_validator,
)
from agents._shared import audit, build_envelope, utc_now_iso

STAGE_DIRS = ("input", "processing", "output", "results")
SOURCE_AGENT = "integrator"

# Maps a configurable stage name (config.DEFAULT_STAGES) to its agent module. The validator is not
# here — it is the always-on entry gate handled explicitly in _run_one. We store the module (not the
# bound function) so process_message is resolved at call time — late binding keeps the stage loop in
# step with monkeypatching and any runtime reassignment of an agent's process_message.
STAGE_MODULES = {
    "fraud_detector": fraud_detector,
    "compliance_checker": compliance_checker,
    "notification_agent": notification_agent,
}


def _setup_dirs(base: Path, reset: bool) -> dict[str, Path]:
    dirs = {name: base / name for name in STAGE_DIRS}
    for path in dirs.values():
        if reset and path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def _write(path: Path, message: dict[str, Any]) -> None:
    path.write_text(json.dumps(message, indent=2), encoding="utf-8")


def _move(message: dict[str, Any], txn_id: str, src: Path, dst: Path) -> None:
    """Persist ``message`` to dst/<id>.json and remove the src copy (lifecycle move)."""
    _write(dst / f"{txn_id}.json", message)
    stale = src / f"{txn_id}.json"
    if stale.exists():
        stale.unlink()


def _run_one(
    record: dict[str, Any],
    dirs: dict[str, Path],
    audit_log: Path,
    stages: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Run a single transaction through the validator gate + enabled stages.

    ``stages`` selects which downstream stages run (default: ``config.ENABLED_STAGES``); the
    transaction_validator always runs first. Each stage moves the message through the
    output -> processing -> output lifecycle; the terminal message lands in results/.
    """
    active = config.ENABLED_STAGES if stages is None else stages
    txn_id = record.get("transaction_id", "UNKNOWN")

    # input -> processing
    message = build_envelope(
        source_agent=SOURCE_AGENT, target_agent="transaction_validator", data=dict(record)
    )
    _write(dirs["input"] / f"{txn_id}.json", message)
    _move(message, txn_id, dirs["input"], dirs["processing"])

    # validation stage (always on)
    message = transaction_validator.process_message(message, audit_log)
    _move(message, txn_id, dirs["processing"], dirs["output"])

    if message["target_agent"] == "results":  # rejected -> short-circuit
        _move(message, txn_id, dirs["output"], dirs["results"])
        return message

    # configurable downstream stages, in order
    for stage in active:
        module = STAGE_MODULES[stage]
        _move(message, txn_id, dirs["output"], dirs["processing"])
        message = module.process_message(message, audit_log)
        _move(message, txn_id, dirs["processing"], dirs["output"])

    # terminal: output -> results
    _move(message, txn_id, dirs["output"], dirs["results"])
    return message


def _summarise(messages: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "total": len(messages),
        "validated": 0,
        "rejected": 0,
        "flagged": 0,
        "approved": 0,
        "held": 0,
        "notified": 0,
        "errors": 0,
    }
    transactions = []
    for msg in messages:
        data = msg["data"]
        status = data.get("status")
        if status == "rejected":
            counts["rejected"] += 1
        elif status == "error":
            counts["errors"] += 1
        else:
            counts["validated"] += 1
        if data.get("flagged"):
            counts["flagged"] += 1
        decision = data.get("decision")
        if decision == "approve":
            counts["approved"] += 1
        elif decision == "hold":
            counts["held"] += 1
        notifications = data.get("notifications") or []
        if notifications:
            counts["notified"] += 1
        transactions.append(
            {
                "transaction_id": data.get("transaction_id"),
                "status": status,
                "reason": data.get("reason"),
                "risk_score": data.get("risk_score"),
                "flagged": data.get("flagged"),
                "decision": decision,
                "decision_reason": data.get("decision_reason"),
                "notifications": notifications,
            }
        )
    return {"generated_at": utc_now_iso(), "counts": counts, "transactions": transactions}


def _terminal_result(
    record: dict[str, Any],
    dirs: dict[str, Path],
    audit_log: Path,
    *,
    status: str,
    reason: str,
    filename: str,
    outcome: str,
) -> dict[str, Any]:
    """Write a terminal (rejected/error/duplicate) result directly to results/ and audit it."""
    txn_id = record.get("transaction_id", "UNKNOWN")
    data = dict(record)
    data["status"] = status
    data["reason"] = reason
    message = build_envelope(source_agent=SOURCE_AGENT, target_agent="results", data=data)
    _write(dirs["results"] / filename, message)
    audit(audit_log, agent=SOURCE_AGENT, transaction_id=txn_id, outcome=outcome)
    return message


def run_pipeline(
    transactions_path: str = "sample-transactions.json",
    base_dir: str = "shared",
    reset: bool = True,
) -> dict[str, Any]:
    """Run the full pipeline over every transaction and return the summary dict.

    Each transaction is processed in isolation: a failure on one record is captured as an
    ``error`` result (so it still lands in results/) and never aborts the run. Duplicate
    transaction ids are rejected rather than silently overwriting an earlier result.
    """
    source = Path(transactions_path)
    records = json.loads(source.read_text(encoding="utf-8"))

    base = Path(base_dir)
    dirs = _setup_dirs(base, reset)
    audit_log = dirs["results"] / "audit.log"

    terminal_messages: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for record in records:
        txn_id = record.get("transaction_id", "UNKNOWN")
        if txn_id in seen:
            seen[txn_id] += 1
            terminal_messages.append(
                _terminal_result(
                    record,
                    dirs,
                    audit_log,
                    status="rejected",
                    reason="duplicate_transaction_id",
                    filename=f"{txn_id}.dup{seen[txn_id]}.json",
                    outcome="rejected:duplicate_transaction_id",
                )
            )
            continue
        seen[txn_id] = 0
        try:
            terminal_messages.append(_run_one(record, dirs, audit_log))
        except Exception as exc:  # safety net: one bad record must not abort the run
            terminal_messages.append(
                _terminal_result(
                    record,
                    dirs,
                    audit_log,
                    status="error",
                    reason=f"pipeline_error:{type(exc).__name__}",
                    filename=f"{txn_id}.json",
                    outcome=f"error:{type(exc).__name__}",
                )
            )

    summary = _summarise(terminal_messages)
    _write(dirs["results"] / "summary.json", summary)
    return summary


def process_one(
    record: dict[str, Any],
    base_dir: str = "shared",
    stages: object = None,
) -> dict[str, Any]:
    """Process a single transaction inline (the REST gateway's entry point).

    Uses append semantics (``reset=False``) so submissions accumulate in shared/results/. ``stages``
    is validated via ``config.resolve_stages`` (None -> ``config.ENABLED_STAGES``). Returns the
    terminal transaction ``data`` dict (status/risk_score/decision/notifications/...).
    """
    active = config.ENABLED_STAGES if stages is None else config.resolve_stages(stages)
    base = Path(base_dir)
    dirs = _setup_dirs(base, reset=False)
    audit_log = dirs["results"] / "audit.log"
    message = _run_one(record, dirs, audit_log, active)
    return message["data"]


def rebuild_summary(base_dir: str = "shared") -> dict[str, Any]:
    """Recompute shared/results/summary.json from every result envelope on disk and return it."""
    results_dir = Path(base_dir) / "results"
    messages: list[dict[str, Any]] = []
    if results_dir.exists():
        for path in sorted(results_dir.glob("*.json")):
            if path.name == "summary.json":
                continue
            try:
                messages.append(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue  # skip an unreadable/partial file rather than failing the whole summary
    summary = _summarise(messages)
    results_dir.mkdir(parents=True, exist_ok=True)
    _write(results_dir / "summary.json", summary)
    return summary


def _print_summary(summary: dict[str, Any]) -> None:
    counts = summary["counts"]
    print("\n=== Pipeline run summary ===")
    print(
        f"total={counts['total']} validated={counts['validated']} "
        f"rejected={counts['rejected']} flagged={counts['flagged']} "
        f"approved={counts['approved']} held={counts['held']} "
        f"errors={counts.get('errors', 0)}"
    )
    print(f"{'TXN':<8} {'STATUS':<10} {'RISK':<5} {'DECISION':<9} REASON")
    for txn in summary["transactions"]:
        reason = txn["decision_reason"] or txn["reason"] or "-"
        print(
            f"{txn['transaction_id']:<8} {str(txn['status']):<10} "
            f"{str(txn['risk_score'] if txn['risk_score'] is not None else '-'):<5} "
            f"{str(txn['decision'] or '-'):<9} {reason}"
        )


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "sample-transactions.json"
    summary = run_pipeline(path)
    _print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
