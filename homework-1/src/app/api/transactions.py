from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.domain.enums import TransactionStatus, TransactionType
from app.domain.models import Transaction, TransactionCreate
from app.services.csv_export import transactions_to_csv
from app.services.store import InMemoryTransactionStore, get_store

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _bad_request(field: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": "Validation failed", "details": [{"field": field, "message": message}]},
    )


def _parse_one(value: str, *, end_of_day: bool) -> datetime:
    """Parse an ISO 8601 date or datetime, coercing naive results to UTC."""
    if "T" in value:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    dt = datetime.fromisoformat(value).replace(tzinfo=UTC)
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt


def _parse_date_range(from_str: Optional[str], to_str: Optional[str]):
    """Return (from_dt, to_dt) tz-aware datetimes, or (False, False) on parse error."""
    try:
        from_dt = _parse_one(from_str, end_of_day=False) if from_str else None
        to_dt = _parse_one(to_str, end_of_day=True) if to_str else None
    except ValueError:
        return False, False
    return from_dt, to_dt


@router.post("", status_code=201)
def create_transaction(
    payload: TransactionCreate,
    store: InMemoryTransactionStore = Depends(get_store),
) -> dict:
    txn = Transaction(
        id=str(uuid.uuid4()),
        fromAccount=payload.from_account,
        toAccount=payload.to_account,
        amount=payload.amount,
        currency=payload.currency,
        type=payload.type,
        status=TransactionStatus.COMPLETED,
        timestamp=datetime.now(UTC).isoformat(),
    )
    store.insert(txn)
    return txn.model_dump_camel()


@router.get("/export")
def export_transactions(
    format: str = Query(..., description="Export format"),
    accountId: Optional[str] = Query(None),
    type: Optional[TransactionType] = Query(None),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    store: InMemoryTransactionStore = Depends(get_store),
) -> Response:
    if format != "csv":
        return _bad_request("format", "Unsupported format; use 'csv'")

    from_date, to_date = _parse_date_range(from_, to)
    if from_date is False or to_date is False:
        return _bad_request("from/to", "Invalid date format; use ISO 8601 (YYYY-MM-DD)")

    transactions = store.filter(
        account_id=accountId,
        txn_type=type,
        from_date=from_date,
        to_date=to_date,
    )
    return Response(
        content=transactions_to_csv(transactions),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
    )


@router.get("")
def list_transactions(
    accountId: Optional[str] = Query(None),
    type: Optional[TransactionType] = Query(None),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    store: InMemoryTransactionStore = Depends(get_store),
) -> list[dict]:
    from_date, to_date = _parse_date_range(from_, to)
    if from_date is False or to_date is False:
        return _bad_request("from/to", "Invalid date format; use ISO 8601 (YYYY-MM-DD)")

    transactions = store.filter(
        account_id=accountId,
        txn_type=type,
        from_date=from_date,
        to_date=to_date,
    )
    return [t.model_dump_camel() for t in transactions]


@router.get("/{txn_id}")
def get_transaction(
    txn_id: str,
    store: InMemoryTransactionStore = Depends(get_store),
) -> dict:
    txn = store.get(txn_id)
    if txn is None:
        return JSONResponse(status_code=404, content={"error": "Transaction not found"})
    return txn.model_dump_camel()
