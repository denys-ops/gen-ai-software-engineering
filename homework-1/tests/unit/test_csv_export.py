"""Unit tests for CSV export service."""
import csv
import io
from decimal import Decimal

from app.services.csv_export import transactions_to_csv, _COLUMNS
from app.domain.models import Transaction
from app.domain.enums import TransactionType, TransactionStatus


def make_txn(txn_id="t1", from_acc=None, to_acc="ACC-12345") -> Transaction:
    return Transaction(
        id=txn_id,
        fromAccount=from_acc,
        toAccount=to_acc,
        amount=Decimal("100.50"),
        currency="USD",
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.COMPLETED,
        timestamp="2024-01-15T10:00:00+00:00",
    )


def parse_csv(content: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(content)))


def test_empty_list_returns_header_only():
    content = transactions_to_csv([])
    rows = parse_csv(content)
    assert rows == []
    assert content.startswith(",".join(_COLUMNS))


def test_header_matches_columns():
    header_line = transactions_to_csv([]).splitlines()[0]
    assert header_line == ",".join(_COLUMNS)


def test_single_transaction_row_fields():
    txn = make_txn()
    rows = parse_csv(transactions_to_csv([txn]))
    assert len(rows) == 1
    assert rows[0]["id"] == txn.id
    assert rows[0]["currency"] == "USD"
    assert rows[0]["type"] == "deposit"
    assert rows[0]["status"] == "completed"
    assert rows[0]["amount"] == "100.5"  # float representation
    assert rows[0]["toAccount"] == "ACC-12345"
    assert rows[0]["fromAccount"] == ""   # absent → empty string


def test_multiple_rows_preserved_in_order():
    t1 = make_txn("id-1")
    t2 = make_txn("id-2")
    rows = parse_csv(transactions_to_csv([t1, t2]))
    assert [r["id"] for r in rows] == ["id-1", "id-2"]


def test_transfer_has_both_accounts():
    txn = Transaction(
        id="t-transfer",
        fromAccount="ACC-11111",
        toAccount="ACC-22222",
        amount=Decimal("25.00"),
        currency="EUR",
        type=TransactionType.TRANSFER,
        status=TransactionStatus.COMPLETED,
        timestamp="2024-06-01T00:00:00+00:00",
    )
    rows = parse_csv(transactions_to_csv([txn]))
    assert rows[0]["fromAccount"] == "ACC-11111"
    assert rows[0]["toAccount"] == "ACC-22222"
