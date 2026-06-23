"""Notification / Alerting agent.

The terminal pipeline agent: runs the configurable rule engine (rules.json) against the
fully-enriched transaction (validated + fraud-scored + compliance-decided) and attaches the
matched notifications. Routing/alerting behaviour is data-driven — change rules.json, not code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents import rule_engine
from agents._shared import audit, reroute

AGENT_NAME = "notification_agent"


def build_notifications(transaction: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the notifications produced by the rule engine for this transaction."""
    return rule_engine.evaluate(transaction)


def process_message(
    message: dict[str, Any], audit_log: Path | str | None = None
) -> dict[str, Any]:
    """Attach rule-engine notifications to the transaction and route it to results."""
    transaction = dict(message["data"])
    txn_id = transaction.get("transaction_id", "UNKNOWN")

    notifications = build_notifications(transaction)
    transaction["notifications"] = notifications

    outcome = f"notified:{len(notifications)}" if notifications else "no_notification"
    audit(audit_log, agent=AGENT_NAME, transaction_id=txn_id, outcome=outcome)

    return reroute(message, source_agent=AGENT_NAME, target_agent="results", data=transaction)
