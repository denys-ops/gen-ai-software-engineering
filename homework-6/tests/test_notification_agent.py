"""Unit tests for agents/notification_agent.py."""

from __future__ import annotations

from pathlib import Path

from agents import notification_agent as na


class TestBuildNotifications:
    def test_flagged_transaction_produces_notifications(self, make_txn):
        # The 'high-fraud' rule in rules.json fires when flagged == true.
        txn = make_txn(flagged=True)
        notifications = na.build_notifications(txn)
        assert isinstance(notifications, list)
        assert len(notifications) >= 1
        # Every notification must have at minimum rule_id, channel, priority.
        for n in notifications:
            assert "rule_id" in n
            assert "channel" in n
            assert "priority" in n

    def test_clean_transaction_no_notifications(self, make_txn):
        # Low-risk, approved, not flagged, small amount — no rule should fire.
        txn = make_txn(
            amount="500.00",
            flagged=False,
            decision="approve",
            decision_reason="passed_compliance",
        )
        notifications = na.build_notifications(txn)
        assert notifications == []

    def test_returns_list(self, make_txn):
        txn = make_txn()
        result = na.build_notifications(txn)
        assert isinstance(result, list)


class TestProcessMessage:
    def test_routes_to_results(self, make_message):
        msg = make_message(target="notification_agent")
        out = na.process_message(msg)
        assert out["target_agent"] == "results"

    def test_notifications_attached_to_data(self, make_message):
        msg = make_message(target="notification_agent")
        out = na.process_message(msg)
        assert "notifications" in out["data"]
        assert isinstance(out["data"]["notifications"], list)

    def test_flagged_transaction_gets_notifications(self, make_message):
        # flagged=True triggers the high-fraud rule in rules.json
        msg = make_message(target="notification_agent", flagged=True)
        out = na.process_message(msg)
        assert out["target_agent"] == "results"
        assert len(out["data"]["notifications"]) >= 1
        notification = out["data"]["notifications"][0]
        assert "channel" in notification
        assert "priority" in notification
        assert "rule_id" in notification

    def test_clean_transaction_empty_notifications(self, make_message):
        msg = make_message(
            target="notification_agent",
            amount="500.00",
            flagged=False,
            decision="approve",
            decision_reason="passed_compliance",
        )
        out = na.process_message(msg)
        assert out["data"]["notifications"] == []

    def test_returns_new_envelope_shape(self, make_message):
        msg = make_message(target="notification_agent")
        out = na.process_message(msg)
        # Must be a proper message envelope
        assert "message_id" in out
        assert "timestamp" in out
        assert "source_agent" in out
        assert out["source_agent"] == "notification_agent"
        assert "data" in out

    def test_audit_log_written(self, make_message, tmp_path):
        msg = make_message(target="notification_agent", transaction_id="AUDITME")
        audit_path = tmp_path / "audit.log"
        na.process_message(msg, audit_log=audit_path)
        assert audit_path.exists()
        content = audit_path.read_text(encoding="utf-8")
        assert "AUDITME" in content

    def test_audit_log_contains_outcome_notified(self, make_message, tmp_path):
        msg = make_message(target="notification_agent", flagged=True, transaction_id="NOTIF01")
        audit_path = tmp_path / "audit.log"
        na.process_message(msg, audit_log=audit_path)
        content = audit_path.read_text(encoding="utf-8")
        assert "notified:" in content

    def test_audit_log_contains_no_notification(self, make_message, tmp_path):
        msg = make_message(
            target="notification_agent",
            transaction_id="CLEAN01",
            amount="500.00",
            flagged=False,
            decision="approve",
            decision_reason="passed_compliance",
        )
        audit_path = tmp_path / "audit.log"
        na.process_message(msg, audit_log=audit_path)
        content = audit_path.read_text(encoding="utf-8")
        assert "no_notification" in content

    def test_no_audit_log_when_path_is_none(self, make_message, tmp_path):
        msg = make_message(target="notification_agent")
        # Must not raise even without audit_log
        out = na.process_message(msg, audit_log=None)
        assert out is not None
