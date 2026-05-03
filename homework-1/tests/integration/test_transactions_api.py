"""Integration tests for POST/GET /transactions and GET /transactions/:id."""

DEPOSIT_PAYLOAD = {
    "toAccount": "ACC-12345",
    "amount": 100.50,
    "currency": "USD",
    "type": "deposit",
}

TRANSFER_PAYLOAD = {
    "fromAccount": "ACC-11111",
    "toAccount": "ACC-22222",
    "amount": 25.00,
    "currency": "EUR",
    "type": "transfer",
}

WITHDRAWAL_PAYLOAD = {
    "fromAccount": "ACC-12345",
    "amount": 30.00,
    "currency": "USD",
    "type": "withdrawal",
}


# ── POST /transactions ─────────────────────────────────────────────────────────

class TestCreateTransaction:
    def test_deposit_returns_201(self, client):
        resp = client.post("/transactions", json=DEPOSIT_PAYLOAD)
        assert resp.status_code == 201

    def test_response_contains_auto_id(self, client):
        resp = client.post("/transactions", json=DEPOSIT_PAYLOAD)
        data = resp.json()
        assert "id" in data
        assert len(data["id"]) > 0

    def test_response_contains_timestamp(self, client):
        resp = client.post("/transactions", json=DEPOSIT_PAYLOAD)
        assert "timestamp" in resp.json()

    def test_status_is_completed(self, client):
        resp = client.post("/transactions", json=DEPOSIT_PAYLOAD)
        assert resp.json()["status"] == "completed"

    def test_response_echoes_fields(self, client):
        resp = client.post("/transactions", json=DEPOSIT_PAYLOAD)
        data = resp.json()
        assert data["toAccount"] == "ACC-12345"
        assert data["amount"] == 100.50
        assert data["currency"] == "USD"
        assert data["type"] == "deposit"

    def test_transfer_both_accounts(self, client):
        resp = client.post("/transactions", json=TRANSFER_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["fromAccount"] == "ACC-11111"
        assert data["toAccount"] == "ACC-22222"

    def test_withdrawal_only_from_account(self, client):
        resp = client.post("/transactions", json=WITHDRAWAL_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["fromAccount"] == "ACC-12345"
        assert resp.json().get("toAccount") is None

    def test_two_transactions_get_distinct_ids(self, client):
        id1 = client.post("/transactions", json=DEPOSIT_PAYLOAD).json()["id"]
        id2 = client.post("/transactions", json=DEPOSIT_PAYLOAD).json()["id"]
        assert id1 != id2


# ── GET /transactions ──────────────────────────────────────────────────────────

class TestListTransactions:
    def test_empty_returns_empty_list(self, client):
        resp = client.get("/transactions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_created_transactions(self, client):
        client.post("/transactions", json=DEPOSIT_PAYLOAD)
        client.post("/transactions", json=TRANSFER_PAYLOAD)
        resp = client.get("/transactions")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ── GET /transactions/:id ──────────────────────────────────────────────────────

class TestGetTransaction:
    def test_returns_transaction_by_id(self, client):
        created_id = client.post("/transactions", json=DEPOSIT_PAYLOAD).json()["id"]
        resp = client.get(f"/transactions/{created_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created_id

    def test_unknown_id_returns_404(self, client):
        resp = client.get("/transactions/nonexistent-id")
        assert resp.status_code == 404
        assert "error" in resp.json()
