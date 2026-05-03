from __future__ import annotations

import csv
import io

from app.domain.models import Transaction

_COLUMNS = ["id", "type", "status", "currency", "amount", "fromAccount", "toAccount", "timestamp"]


def transactions_to_csv(transactions: list[Transaction]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_COLUMNS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for txn in transactions:
        row = txn.model_dump_camel()
        row.setdefault("fromAccount", "")
        row.setdefault("toAccount", "")
        writer.writerow({col: row.get(col, "") for col in _COLUMNS})
    return buf.getvalue()
