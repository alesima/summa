"""Pydantic models."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class Account(BaseModel):
    id: Optional[int] = None
    name: str
    type: str = "checking"  # checking | savings | credit | cash | investment
    currency: str = "BRL"


class Category(BaseModel):
    id: Optional[int] = None
    name: str
    kind: str = "expense"  # expense | income
    parent_id: Optional[int] = None


class Transaction(BaseModel):
    id: Optional[int] = None
    account_id: int
    date: date
    amount_cents: int  # signed: income positive, expense negative
    description: str
    category_id: Optional[int] = None
    notes: Optional[str] = None
    raw: Optional[str] = None


class Budget(BaseModel):
    id: Optional[int] = None
    category_id: int
    month: str  # YYYY-MM
    amount_cents: int


def to_cents(value: float | str) -> int:
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(d * 100)


def from_cents(cents: int) -> str:
    from decimal import Decimal
    return f"{Decimal(cents) / 100:.2f}"


def fmt_date(iso: str) -> str:
    """Format an ISO date (YYYY-MM-DD) as DD/MM/YYYY for display."""
    if not iso:
        return iso
    try:
        from datetime import datetime
        return datetime.strptime(str(iso), "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(iso)
