"""Integration tests: invalid payloads return 400 with structured error bodies."""

BASE = {"toAccount": "ACC-12345", "amount": 100.0, "currency": "USD", "type": "deposit"}


def _post(client, **overrides):
    payload = {**BASE, **overrides}
    return client.post("/transactions", json=payload)


def assert_400_with_details(resp):
    assert resp.status_code == 400
    body = resp.json()
    assert body.get("error") == "Validation failed"
    assert isinstance(body.get("details"), list)
    assert len(body["details"]) > 0
    for detail in body["details"]:
        assert "field" in detail
        assert "message" in detail


class TestAmountValidation:
    def test_zero_amount(self, client):
        assert_400_with_details(_post(client, amount=0))

    def test_negative_amount(self, client):
        assert_400_with_details(_post(client, amount=-5))

    def test_too_many_decimal_places(self, client):
        assert_400_with_details(_post(client, amount=1.234))

    def test_missing_amount(self, client):
        payload = {k: v for k, v in BASE.items() if k != "amount"}
        assert client.post("/transactions", json=payload).status_code == 400


class TestAccountValidation:
    def test_bad_account_format(self, client):
        assert_400_with_details(_post(client, toAccount="12345"))

    def test_lowercase_acc_prefix(self, client):
        assert_400_with_details(_post(client, toAccount="acc-12345"))


class TestCurrencyValidation:
    def test_unknown_currency(self, client):
        assert_400_with_details(_post(client, currency="XYZ"))

    def test_lowercase_currency(self, client):
        assert_400_with_details(_post(client, currency="usd"))


class TestTypeAccountConsistency:
    def test_transfer_without_from(self, client):
        assert client.post("/transactions", json={
            "toAccount": "ACC-12345", "amount": 10, "currency": "USD", "type": "transfer"
        }).status_code == 400

    def test_deposit_with_from_account(self, client):
        assert client.post("/transactions", json={
            "fromAccount": "ACC-11111", "toAccount": "ACC-22222",
            "amount": 10, "currency": "USD", "type": "deposit"
        }).status_code == 400
