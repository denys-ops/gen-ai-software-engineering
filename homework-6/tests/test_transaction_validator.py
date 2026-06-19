"""Unit tests for the Transaction Validator agent."""

from __future__ import annotations

from agents import transaction_validator as v


class TestValidate:
    def test_valid_transaction(self, make_txn):
        ok, reason = v.validate(make_txn())
        assert ok and reason is None

    def test_missing_field(self, make_txn):
        txn = make_txn()
        del txn["currency"]
        ok, reason = v.validate(txn)
        assert not ok and reason == "missing_field:currency"

    def test_empty_field_treated_as_missing(self, make_txn):
        ok, reason = v.validate(make_txn(currency=""))
        assert not ok and reason == "missing_field:currency"

    def test_unsupported_currency(self, make_txn):
        ok, reason = v.validate(make_txn(currency="XYZ"))
        assert not ok and reason == "unsupported_currency"

    def test_bad_account_format(self, make_txn):
        ok, reason = v.validate(make_txn(source_account="ACC-12"))
        assert not ok and reason == "invalid_account_format:source_account"

    def test_zero_amount(self, make_txn):
        ok, reason = v.validate(make_txn(amount="0.00"))
        assert not ok and reason == "zero_amount"

    def test_negative_non_refund_rejected(self, make_txn):
        ok, reason = v.validate(make_txn(amount="-5.00"))
        assert not ok and reason == "negative_amount_not_allowed"

    def test_negative_refund_allowed(self, make_txn):
        ok, reason = v.validate(make_txn(amount="-100.00", transaction_type="refund"))
        assert ok and reason is None

    def test_too_many_decimal_places(self, make_txn):
        ok, reason = v.validate(make_txn(amount="10.999"))
        assert not ok and reason == "too_many_decimal_places"

    def test_non_numeric_amount(self, make_txn):
        ok, reason = v.validate(make_txn(amount="abc"))
        assert not ok and reason == "invalid_amount"


class TestProcessMessage:
    def test_validated_routes_to_fraud(self, make_message):
        out = v.process_message(make_message())
        assert out["data"]["status"] == "validated"
        assert out["target_agent"] == "fraud_detector"

    def test_rejected_routes_to_results(self, make_message):
        out = v.process_message(make_message(currency="XYZ"))
        assert out["data"]["status"] == "rejected"
        assert out["data"]["reason"] == "unsupported_currency"
        assert out["target_agent"] == "results"

    def test_writes_audit(self, make_message, tmp_path):
        log = tmp_path / "audit.log"
        v.process_message(make_message(), log)
        assert log.exists() and "validated" in log.read_text()


class TestDryRun:
    def test_dry_run_counts(self, tmp_path):
        import json

        records = [
            {"transaction_id": "A", "timestamp": "2026-03-16T09:00:00Z",
             "source_account": "ACC-1001", "destination_account": "ACC-2001",
             "amount": "10.00", "currency": "USD", "transaction_type": "transfer"},
            {"transaction_id": "B", "timestamp": "2026-03-16T09:00:00Z",
             "source_account": "ACC-1001", "destination_account": "ACC-2001",
             "amount": "10.00", "currency": "XYZ", "transaction_type": "transfer"},
        ]
        path = tmp_path / "txns.json"
        path.write_text(json.dumps(records))
        report = v.dry_run(str(path))
        assert report["total"] == 2 and report["valid"] == 1 and report["invalid"] == 1

    def test_main_dry_run(self, capsys, monkeypatch, tmp_path):
        import json

        path = tmp_path / "txns.json"
        path.write_text(json.dumps([]))
        rc = v.main(["--dry-run", str(path)])
        assert rc == 0
        assert "Validation dry-run" in capsys.readouterr().out

    def test_main_without_flag_returns_usage(self, capsys):
        rc = v.main([])
        assert rc == 2
        assert "usage" in capsys.readouterr().out
