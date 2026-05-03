from __future__ import annotations

import re
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from app.domain.currencies import VALID_CURRENCIES
from app.domain.enums import TransactionStatus, TransactionType

_ACCOUNT_RE = re.compile(r"^ACC-[A-Za-z0-9]{5,}$")


class TransactionCreate(BaseModel):
    from_account: Optional[str] = Field(None, alias="fromAccount")
    to_account: Optional[str] = Field(None, alias="toAccount")
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str
    type: TransactionType

    model_config = {"populate_by_name": True}

    @field_validator("from_account", "to_account", mode="before")
    @classmethod
    def validate_account_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _ACCOUNT_RE.match(v):
            raise ValueError(
                f"Account must match ACC-XXXXX format (≥5 alphanumeric chars after dash), got: {v!r}"
            )
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v not in VALID_CURRENCIES:
            raise ValueError(f"Invalid ISO 4217 currency code: {v!r}")
        return v

    @model_validator(mode="after")
    def validate_account_fields_for_type(self) -> TransactionCreate:
        t = self.type
        if t == TransactionType.TRANSFER:
            if self.from_account is None or self.to_account is None:
                raise ValueError("transfer requires both fromAccount and toAccount")
        elif t == TransactionType.DEPOSIT:
            if self.to_account is None:
                raise ValueError("deposit requires toAccount")
            if self.from_account is not None:
                raise ValueError("deposit must not include fromAccount")
        elif t == TransactionType.WITHDRAWAL:
            if self.from_account is None:
                raise ValueError("withdrawal requires fromAccount")
            if self.to_account is not None:
                raise ValueError("withdrawal must not include toAccount")
        return self


class Transaction(BaseModel):
    id: str
    from_account: Optional[str] = Field(None, alias="fromAccount")
    to_account: Optional[str] = Field(None, alias="toAccount")
    amount: Decimal
    currency: str
    type: TransactionType
    status: TransactionStatus
    timestamp: str

    model_config = {"populate_by_name": True}

    @field_serializer("amount")
    def serialize_amount(self, v: Decimal) -> float:
        return float(v)

    def model_dump_camel(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    details: list[ErrorDetail] = Field(default_factory=list)
