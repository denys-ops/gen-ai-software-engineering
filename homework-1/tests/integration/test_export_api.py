"""Integration tests for GET /transactions/export."""

DEPOSIT = {"toAccount": "ACC-11111", "amount": 100.0, "currency": "USD", "type": "deposit"}
TRANSFER = {
    "fromAccount": "ACC-11111", "toAccount": "ACC-22222",
    "amount": 25.0, "currency": "EUR", "type": "transfer",
}


class TestCsvExport:
    def test_returns_200(self, client):
        resp = client.get("/transactions/export", params={"format": "csv"})
        assert resp.status_code == 200

    def test_content_type_is_csv(self, client):
        resp = client.get("/transactions/export", params={"format": "csv"})
        assert "text/csv" in resp.headers["content-type"]

    def test_content_disposition_attachment(self, client):
        resp = client.get("/transactions/export", params={"format": "csv"})
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert "transactions.csv" in resp.headers.get("content-disposition", "")

    def test_empty_store_returns_header_only(self, client):
        resp = client.get("/transactions/export", params={"format": "csv"})
        lines = resp.text.strip().splitlines()
        assert len(lines) == 1
        assert "id" in lines[0]

    def test_seeded_data_has_correct_row_count(self, client):
        client.post("/transactions", json=DEPOSIT)
        client.post("/transactions", json=TRANSFER)
        resp = client.get("/transactions/export", params={"format": "csv"})
        lines = resp.text.strip().splitlines()
        assert len(lines) == 3  # 1 header + 2 data rows

    def test_unknown_format_returns_400(self, client):
        resp = client.get("/transactions/export", params={"format": "xml"})
        assert resp.status_code == 400

    def test_missing_format_returns_400(self, client):
        resp = client.get("/transactions/export")
        assert resp.status_code == 400

    def test_export_respects_account_filter(self, client):
        client.post("/transactions", json=DEPOSIT)
        client.post("/transactions", json=TRANSFER)
        resp = client.get("/transactions/export", params={
            "format": "csv", "accountId": "ACC-22222"
        })
        lines = resp.text.strip().splitlines()
        assert len(lines) == 2  # header + 1 transfer row only
