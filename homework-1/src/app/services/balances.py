from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.domain.enums import TransactionType
from app.domain.models import Transaction


def compute_balances(transactions: list[Transaction], account_id: str) -> dict[str, Decimal]:
    balances: dict[str, Decimal] = defaultdict(Decimal)

    for txn in transactions:
        if txn.to_account == account_id:
            balances[txn.currency] += txn.amount
        if txn.from_account == account_id:
            balances[txn.currency] -= txn.amount

    return {k: v for k, v in balances.items() if v != 0} if balances else {}
