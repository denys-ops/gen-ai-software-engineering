from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.domain.enums import TransactionType
from app.domain.models import Transaction


class InMemoryTransactionStore:
    def __init__(self) -> None:
        self._data: dict[str, Transaction] = {}
        self._order: list[str] = []

    def insert(self, txn: Transaction) -> None:
        self._data[txn.id] = txn
        self._order.append(txn.id)

    def get(self, txn_id: str) -> Optional[Transaction]:
        return self._data.get(txn_id)

    def list_all(self) -> list[Transaction]:
        return [self._data[i] for i in self._order]

    def filter(
        self,
        *,
        account_id: Optional[str] = None,
        txn_type: Optional[TransactionType] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[Transaction]:
        results = self.list_all()

        if account_id is not None:
            results = [
                t for t in results
                if t.from_account == account_id or t.to_account == account_id
            ]

        if txn_type is not None:
            results = [t for t in results if t.type == txn_type]

        if from_date is not None:
            results = [
                t for t in results
                if datetime.fromisoformat(t.timestamp.replace("Z", "+00:00")) >= from_date
            ]

        if to_date is not None:
            results = [
                t for t in results
                if datetime.fromisoformat(t.timestamp.replace("Z", "+00:00")) <= to_date
            ]

        return results


_store = InMemoryTransactionStore()


def get_store() -> InMemoryTransactionStore:
    return _store
