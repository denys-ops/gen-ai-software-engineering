"""Compliance Checker agent.

Makes the terminal compliance decision (approve | hold | reject) for a fraud-scored
transaction, applying extra scrutiny to wire transfers, cross-border, and sanctioned countries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import config
from agents._shared import audit, country_of, reroute

AGENT_NAME = "compliance_checker"


def decide(transaction: dict[str, Any]) -> tuple[str, str]:
    """Return (decision, decision_reason) for a fraud-scored transaction."""
    country = country_of(transaction)
    txn_type = transaction.get("transaction_type")
    triggered = transaction.get("triggered_rules") or []
    flagged = bool(transaction.get("flagged"))

    if country in config.SANCTIONED_COUNTRIES:
        return "hold", "sanctioned_country"
    if flagged:
        return "hold", "high_fraud_risk"
    if txn_type in config.HIGH_SCRUTINY_TYPES and "high_value" in triggered:
        return "hold", "wire_high_value_review"
    return "approve", "passed_compliance"


def process_message(
    message: dict[str, Any], audit_log: Path | str | None = None
) -> dict[str, Any]:
    """Apply the compliance decision and route the message to results."""
    transaction = dict(message["data"])
    txn_id = transaction.get("transaction_id", "UNKNOWN")

    decision, reason = decide(transaction)
    transaction["decision"] = decision
    transaction["decision_reason"] = reason

    audit(audit_log, agent=AGENT_NAME, transaction_id=txn_id, outcome=f"{decision}:{reason}")

    return reroute(message, source_agent=AGENT_NAME, target_agent="results", data=transaction)
