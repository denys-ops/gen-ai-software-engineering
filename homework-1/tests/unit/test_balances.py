"""Unit tests for balance computation service."""
from decimal import Decimal
from app.services.balances import compute_balances
from app.domain.models import Transaction
from app.domain.enums import TransactionType, TransactionStatus


def make_txn(txn_id, type, amount, currency, from_acc=None, to_acc=None) -> Transaction:
    return Transaction(
        id=txn_id,
        fromAccount=from_acc,
        toAccount=to_acc,
        amount=Decimal(str(amount)),
        currency=currency,
        type=type,
        status=TransactionStatus.COMPLETED,
        timestamp="2024-01-01T00:00:00Z",
    )


ACC = "ACC-12345"
OTHER = "ACC-99999"


def test_no_transactions_returns_empty_balances():
    assert compute_balances([], ACC) == {}


def test_deposit_increases_balance():
    txns = [make_txn("1", TransactionType.DEPOSIT, 100, "USD", to_acc=ACC)]
    assert compute_balances(txns, ACC) == {"USD": Decimal("100.00")}


def test_withdrawal_decreases_balance():
    txns = [
        make_txn("1", TransactionType.DEPOSIT, 200, "USD", to_acc=ACC),
        make_txn("2", TransactionType.WITHDRAWAL, 50, "USD", from_acc=ACC),
    ]
    assert compute_balances(txns, ACC) == {"USD": Decimal("150.00")}


def test_transfer_in_increases_balance():
    txns = [make_txn("1", TransactionType.TRANSFER, 75, "USD", from_acc=OTHER, to_acc=ACC)]
    assert compute_balances(txns, ACC) == {"USD": Decimal("75.00")}


def test_transfer_out_decreases_balance():
    txns = [
        make_txn("1", TransactionType.DEPOSIT, 200, "USD", to_acc=ACC),
        make_txn("2", TransactionType.TRANSFER, 50, "USD", from_acc=ACC, to_acc=OTHER),
    ]
    assert compute_balances(txns, ACC) == {"USD": Decimal("150.00")}


def test_multi_currency_separate_balances():
    txns = [
        make_txn("1", TransactionType.DEPOSIT, 100, "USD", to_acc=ACC),
        make_txn("2", TransactionType.DEPOSIT, 200, "EUR", to_acc=ACC),
    ]
    result = compute_balances(txns, ACC)
    assert result == {"USD": Decimal("100.00"), "EUR": Decimal("200.00")}


def test_unrelated_transactions_not_counted():
    txns = [make_txn("1", TransactionType.DEPOSIT, 500, "USD", to_acc=OTHER)]
    assert compute_balances(txns, ACC) == {}


def test_decimal_precision_no_float_drift():
    txns = [
        make_txn("1", TransactionType.DEPOSIT, "100.10", "USD", to_acc=ACC),
        make_txn("2", TransactionType.DEPOSIT, "100.10", "USD", to_acc=ACC),
        make_txn("3", TransactionType.DEPOSIT, "100.10", "USD", to_acc=ACC),
    ]
    result = compute_balances(txns, ACC)
    assert result["USD"] == Decimal("300.30")
