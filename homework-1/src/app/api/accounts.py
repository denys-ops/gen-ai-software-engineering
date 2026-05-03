from __future__ import annotations

from fastapi import APIRouter, Depends

from app.services.balances import compute_balances
from app.services.store import InMemoryTransactionStore, get_store

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/{account_id}/balance")
def get_balance(
    account_id: str,
    store: InMemoryTransactionStore = Depends(get_store),
) -> dict:
    balances = compute_balances(store.list_all(), account_id)
    return {
        "accountId": account_id,
        "balances": {k: float(v) for k, v in balances.items()},
    }
