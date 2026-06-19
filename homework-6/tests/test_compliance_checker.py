"""Unit tests for the Compliance Checker agent."""

from __future__ import annotations

from agents import compliance_checker as c


def _scored(make_txn, **overrides):
    txn = make_txn(**overrides)
    txn.setdefault("risk_score", 0)
    txn.setdefault("triggered_rules", [])
    txn.setdefault("flagged", False)
    return txn


class TestDecide:
    def test_clean_approve(self, make_txn):
        decision, reason = c.decide(_scored(make_txn))
        assert decision == "approve" and reason == "passed_compliance"

    def test_flagged_held(self, make_txn):
        decision, reason = c.decide(_scored(make_txn, flagged=True))
        assert decision == "hold" and reason == "high_fraud_risk"

    def test_sanctioned_country_held(self, make_txn):
        decision, reason = c.decide(_scored(make_txn, metadata={"country": "IR"}))
        assert decision == "hold" and reason == "sanctioned_country"

    def test_wire_high_value_held(self, make_txn):
        txn = _scored(
            make_txn,
            transaction_type="wire_transfer",
            triggered_rules=["high_value"],
            flagged=False,
        )
        decision, reason = c.decide(txn)
        assert decision == "hold" and reason == "wire_high_value_review"

    def test_sanctioned_takes_precedence_over_flag(self, make_txn):
        decision, reason = c.decide(
            _scored(make_txn, metadata={"country": "KP"}, flagged=True)
        )
        assert reason == "sanctioned_country"


class TestProcessMessage:
    def test_routes_to_results(self, make_message):
        msg = make_message(target="compliance_checker")
        msg["data"].update({"risk_score": 0, "triggered_rules": [], "flagged": False})
        out = c.process_message(msg)
        assert out["target_agent"] == "results"
        assert out["data"]["decision"] == "approve"
