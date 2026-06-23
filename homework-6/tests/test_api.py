"""Tests for the FastAPI REST gateway (api/main.py).

Uses TestClient (synchronous transport over ASGI). The underlying pipeline writes to the real
shared/ directory — that is intentional and mirrors how the task specifies it. Each test that
POSTs a transaction uses a unique transaction_id to avoid cross-test interference.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _unique_id() -> str:
    return f"TEST-{uuid.uuid4().hex[:8].upper()}"


def _txn(**overrides) -> dict:
    base = {
        "transaction_id": _unique_id(),
        "timestamp": "2026-03-16T09:00:00Z",
        "source_account": "ACC-1001",
        "destination_account": "ACC-2001",
        "amount": "1500.00",
        "currency": "USD",
        "transaction_type": "transfer",
        "metadata": {"channel": "online", "country": "US"},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /transactions
# ---------------------------------------------------------------------------


class TestPostTransactions:
    def test_single_txn_returns_list_of_one(self):
        resp = client.post("/transactions", json=_txn())
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_single_txn_has_transaction_id_and_status(self):
        resp = client.post("/transactions", json=_txn())
        item = resp.json()[0]
        assert "transaction_id" in item
        assert "status" in item

    def test_batch_of_two_returns_list_of_two(self):
        batch = [_txn(), _txn()]
        resp = client.post("/transactions", json=batch)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_stages_fraud_only_has_risk_score_no_decision(self):
        resp = client.post("/transactions?stages=fraud_detector", json=_txn())
        assert resp.status_code == 200
        item = resp.json()[0]
        assert "risk_score" in item
        assert "decision" not in item

    def test_stages_bogus_returns_400(self):
        resp = client.post("/transactions?stages=bogus", json=_txn())
        assert resp.status_code == 400

    def test_default_pipeline_has_decision_and_notifications(self):
        resp = client.post("/transactions", json=_txn())
        assert resp.status_code == 200
        item = resp.json()[0]
        assert "decision" in item
        assert "notifications" in item

    def test_invalid_txn_rejected(self):
        txn = _txn(currency="INVALID")
        resp = client.post("/transactions", json=txn)
        assert resp.status_code == 200
        item = resp.json()[0]
        assert item["status"] == "rejected"


# ---------------------------------------------------------------------------
# GET /transactions/{id}
# ---------------------------------------------------------------------------


class TestGetTransaction:
    def test_found_after_post(self):
        txn = _txn()
        client.post("/transactions", json=txn)
        resp = client.get(f"/transactions/{txn['transaction_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["found"] is True
        assert body["transaction_id"] == txn["transaction_id"]

    def test_not_found_returns_404(self):
        resp = client.get("/transactions/NOPE_DOES_NOT_EXIST_XYZ")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary_200(self):
        resp = client.get("/summary")
        assert resp.status_code == 200

    def test_summary_has_counts_with_notified(self):
        # POST at least one txn to ensure counts are populated
        client.post("/transactions", json=_txn())
        resp = client.get("/summary")
        data = resp.json()
        assert "counts" in data
        assert "notified" in data["counts"]

    def test_summary_counts_total_nonnegative(self):
        resp = client.get("/summary")
        assert resp.json()["counts"]["total"] >= 0


# ---------------------------------------------------------------------------
# GET /rules
# ---------------------------------------------------------------------------


class TestRules:
    def test_rules_200(self):
        resp = client.get("/rules")
        assert resp.status_code == 200

    def test_rules_has_rules_list(self):
        resp = client.get("/rules")
        data = resp.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)

    def test_rules_list_not_empty(self):
        resp = client.get("/rules")
        assert len(resp.json()["rules"]) >= 1


# ---------------------------------------------------------------------------
# GET /config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_config_200(self):
        resp = client.get("/config")
        assert resp.status_code == 200

    def test_config_has_enabled_stages(self):
        resp = client.get("/config")
        data = resp.json()
        assert "enabled_stages" in data
        assert isinstance(data["enabled_stages"], list)

    def test_config_enabled_stages_not_empty(self):
        resp = client.get("/config")
        assert len(resp.json()["enabled_stages"]) > 0


# ---------------------------------------------------------------------------
# GET /transactions (list)
# ---------------------------------------------------------------------------


class TestListTransactions:
    def test_list_transactions_200(self):
        resp = client.get("/transactions")
        assert resp.status_code == 200

    def test_list_transactions_has_count_and_transactions(self):
        resp = client.get("/transactions")
        data = resp.json()
        assert "count" in data
        assert "transactions" in data
        assert isinstance(data["transactions"], list)
