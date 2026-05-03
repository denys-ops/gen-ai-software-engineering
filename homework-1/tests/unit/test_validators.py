"""Unit tests for Pydantic validation rules on TransactionCreate."""
import pytest
from pydantic import ValidationError

from app.domain.models import TransactionCreate


def parse(**kwargs) -> TransactionCreate:
    return TransactionCreate.model_validate(kwargs, by_alias=True)


def expect_error(alias_field: str, **kwargs):
    """Assert that validation raises and the error touches the given alias field name."""
    with pytest.raises(ValidationError) as exc_info:
        parse(**kwargs)
    fields = [str(e["loc"][-1]) for e in exc_info.value.errors()]
    assert alias_field in fields, f"Expected error on {alias_field!r}, got: {fields}"


# ── Amount ─────────────────────────────────────────────────────────────────────

def test_amount_zero_is_invalid():
    expect_error("amount", toAccount="ACC-12345", amount=0, currency="USD", type="deposit")


def test_amount_negative_is_invalid():
    expect_error("amount", toAccount="ACC-12345", amount=-10, currency="USD", type="deposit")


def test_amount_three_decimal_places_is_invalid():
    expect_error("amount", toAccount="ACC-12345", amount=1.234, currency="USD", type="deposit")


def test_amount_two_decimal_places_is_valid():
    txn = parse(toAccount="ACC-12345", amount=99.99, currency="USD", type="deposit")
    assert float(txn.amount) == 99.99


def test_amount_whole_number_is_valid():
    txn = parse(toAccount="ACC-12345", amount=100, currency="USD", type="deposit")
    assert float(txn.amount) == 100.0


# ── Account format ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("account", ["acc-12345", "ACC-12", "12345", "ACC-!!!!!", "ACCABC12345"])
def test_invalid_account_format(account):
    expect_error("toAccount", toAccount=account, amount=10, currency="USD", type="deposit")


@pytest.mark.parametrize("account", ["ACC-12345", "ACC-ABCDE", "ACC-abc12"])
def test_valid_account_format(account):
    txn = parse(toAccount=account, amount=10, currency="USD", type="deposit")
    assert txn.to_account == account


# ── Currency ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("currency", ["usd", "XYZ", "", "US"])
def test_invalid_currency(currency):
    expect_error("currency", toAccount="ACC-12345", amount=10, currency=currency, type="deposit")


@pytest.mark.parametrize("currency", ["USD", "EUR", "GBP", "JPY"])
def test_valid_currency(currency):
    txn = parse(toAccount="ACC-12345", amount=10, currency=currency, type="deposit")
    assert txn.currency == currency


# ── Type / account-field consistency ──────────────────────────────────────────

def test_transfer_missing_from_account_is_invalid():
    with pytest.raises(ValidationError):
        parse(toAccount="ACC-12345", amount=10, currency="USD", type="transfer")


def test_transfer_missing_to_account_is_invalid():
    with pytest.raises(ValidationError):
        parse(fromAccount="ACC-12345", amount=10, currency="USD", type="transfer")


def test_transfer_with_both_accounts_is_valid():
    txn = parse(
        fromAccount="ACC-11111", toAccount="ACC-22222",
        amount=10, currency="USD", type="transfer"
    )
    assert txn.from_account == "ACC-11111"


def test_deposit_with_from_account_is_invalid():
    with pytest.raises(ValidationError):
        parse(
            fromAccount="ACC-11111", toAccount="ACC-22222",
            amount=10, currency="USD", type="deposit"
        )


def test_withdrawal_with_to_account_is_invalid():
    with pytest.raises(ValidationError):
        parse(
            fromAccount="ACC-11111", toAccount="ACC-22222",
            amount=10, currency="USD", type="withdrawal"
        )


def test_deposit_without_to_account_is_invalid():
    with pytest.raises(ValidationError):
        parse(amount=10, currency="USD", type="deposit")


def test_withdrawal_without_from_account_is_invalid():
    with pytest.raises(ValidationError):
        parse(amount=10, currency="USD", type="withdrawal")
