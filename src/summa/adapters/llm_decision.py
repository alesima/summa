"""LLM-backed decision adapter (fallback)."""
from __future__ import annotations

from typing import Any

from .. import ai


class LLMDecisionModel:
    def categorize(self, transactions, categories):
        items = ai.categorize_transactions(transactions, categories)
        out = []
        for it in items:
            out.append({"id": it.get("id"), "category": it.get("category"), "confidence": 1.0})
        return out
