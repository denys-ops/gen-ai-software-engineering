"""Integration tests for GET /transactions filtering and GET /accounts/:id/balance."""

DEPOSIT_ACC1_USD = {"toAccount": "ACC-11111", "amount": 100.0, "currency": "USD", "type": "deposit"}
DEPOSIT_ACC2_EUR = {"toAccount": "ACC-22222", "amount": 50.0, "currency": "EUR", "type": "deposit"}
TRANSFER = {
    "fromAccount": "ACC-11111", "toAccount": "ACC-22222",
    "amount": 25.0, "currency": "USD", "type": "transfer",
}
WITHDRAWAL_ACC1 = {"fromAccount": "ACC-11111", "amount": 10.0, "currency": "USD", "type": "withdrawal"}


def seed(client):
    ids = []
    for payload in [DEPOSIT_ACC1_USD, DEPOSIT_ACC2_EUR, TRANSFER, WITHDRAWAL_ACC1]:
        ids.append(client.post("/transactions", json=payload).json()["id"])
    return ids


# ── Filter by accountId ────────────────────────────────────────────────────────

class TestFilterByAccountId:
    def test_deposit_to_account_appears_in_filter(self, client):
        seed(client)
        resp = client.get("/transactions", params={"accountId": "ACC-11111"})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 3  # deposit, transfer (from), withdrawal (from)

    def test_account_not_in_any_transaction_returns_empty(self, client):
        seed(client)
        resp = client.get("/transactions", params={"accountId": "ACC-99999"})
        assert resp.json() == []

    def test_filter_by_to_account_only(self, client):
        seed(client)
        resp = client.get("/transactions", params={"accountId": "ACC-22222"})
        results = resp.json()
        assert len(results) == 2  # deposit to ACC-22222 + transfer to ACC-22222


# ── Filter by type ─────────────────────────────────────────────────────────────

class TestFilterByType:
    def test_filter_deposits(self, client):
        seed(client)
        resp = client.get("/transactions", params={"type": "deposit"})
        results = resp.json()
        assert all(r["type"] == "deposit" for r in results)
        assert len(results) == 2

    def test_filter_transfers(self, client):
        seed(client)
        resp = client.get("/transactions", params={"type": "transfer"})
        assert len(resp.json()) == 1

    def test_invalid_type_returns_400(self, client):
        assert client.get("/transactions", params={"type": "unknown"}).status_code == 400


# ── Filter by date range ───────────────────────────────────────────────────────

class TestFilterByDateRange:
    def test_from_date_excludes_earlier(self, client):
        seed(client)
        resp = client.get("/transactions", params={"from": "2099-01-01"})
        assert resp.json() == []

    def test_to_date_excludes_later(self, client):
        seed(client)
        resp = client.get("/transactions", params={"to": "2000-01-01"})
        assert resp.json() == []

    def test_wide_date_range_returns_all(self, client):
        seed(client)
        resp = client.get("/transactions", params={"from": "2000-01-01", "to": "2099-01-01"})
        assert len(resp.json()) == 4

    def test_invalid_from_date_returns_400(self, client):
        assert client.get("/transactions", params={"from": "not-a-date"}).status_code == 400

    def test_naive_iso_datetime_does_not_500(self, client):
        """Regression: naive ISO datetime (no tzinfo) must coerce to UTC, not crash."""
        seed(client)
        resp = client.get("/transactions", params={"from": "2024-01-01T00:00:00"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_naive_iso_datetime_to_does_not_500(self, client):
        seed(client)
        resp = client.get("/transactions", params={"to": "2099-01-01T00:00:00"})
        assert resp.status_code == 200
        assert len(resp.json()) == 4

    def test_tz_aware_iso_datetime_works(self, client):
        seed(client)
        resp = client.get("/transactions", params={"from": "2024-01-01T00:00:00+00:00"})
        assert resp.status_code == 200


# ── Combined filters ───────────────────────────────────────────────────────────

class TestCombinedFilters:
    def test_account_and_type(self, client):
        seed(client)
        resp = client.get("/transactions", params={"accountId": "ACC-11111", "type": "deposit"})
        results = resp.json()
        assert len(results) == 1
        assert results[0]["toAccount"] == "ACC-11111"


# ── Balance endpoint ───────────────────────────────────────────────────────────

class TestBalanceEndpoint:
    def test_unknown_account_returns_empty_balances(self, client):
        resp = client.get("/accounts/ACC-99999/balance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["accountId"] == "ACC-99999"
        assert data["balances"] == {}

    def test_balance_after_deposit(self, client):
        client.post("/transactions", json=DEPOSIT_ACC1_USD)
        resp = client.get("/accounts/ACC-11111/balance")
        assert resp.json()["balances"]["USD"] == 100.0

    def test_multi_currency_balances(self, client):
        client.post("/transactions", json=DEPOSIT_ACC1_USD)
        client.post("/transactions", json={
            "toAccount": "ACC-11111", "amount": 200.0, "currency": "EUR", "type": "deposit"
        })
        balances = client.get("/accounts/ACC-11111/balance").json()["balances"]
        assert balances["USD"] == 100.0
        assert balances["EUR"] == 200.0

    def test_balance_after_withdrawal(self, client):
        client.post("/transactions", json=DEPOSIT_ACC1_USD)
        client.post("/transactions", json=WITHDRAWAL_ACC1)
        balances = client.get("/accounts/ACC-11111/balance").json()["balances"]
        assert balances["USD"] == 90.0

    def test_balance_after_transfer_out(self, client):
        client.post("/transactions", json=DEPOSIT_ACC1_USD)
        client.post("/transactions", json=TRANSFER)
        balances = client.get("/accounts/ACC-11111/balance").json()["balances"]
        assert balances["USD"] == 75.0
