"""Port (interface) for decision models."""
from __future__ import annotations

from typing import Protocol, TypedDict


class CategorizationItem(TypedDict, total=False):
    id: int
    category: str
    confidence: float


class DecisionModel(Protocol):
    """A model that makes typed, probabilistic decisions."""

    def categorize(self, transactions: list[dict], categories: list[str]) -> list[CategorizationItem]:
        """Return a category suggestion for each transaction."""
        ...
