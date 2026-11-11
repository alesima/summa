"""Decision service: picks a backend (JEV or LLM) with fallback."""
from __future__ import annotations

import os
from typing import Any

from ..adapters.jev import JEVDecisionModel
from ..adapters.llm_decision import LLMDecisionModel
from ..ports.decision import DecisionModel


def backend_name() -> str:
    return (os.environ.get("SUMMA_DECISION_PROVIDER") or "auto").lower()


def get_decision_model() -> DecisionModel:
    name = backend_name()
    if name == "jev":
        return JEVDecisionModel()
    if name == "llm":
        return LLMDecisionModel()
    # auto: try JEV if configured, else LLM
    jev = JEVDecisionModel()
    try:
        if jev._configured():  # type: ignore[attr-defined]
            return jev
    except Exception:
        pass
    return LLMDecisionModel()


def categorize(transactions: list[dict], categories: list[str]) -> list[dict]:
    model = get_decision_model()
    try:
        return model.categorize(transactions, categories)
    except Exception:
        # Fallback to LLM on any JEV failure.
        return LLMDecisionModel().categorize(transactions, categories)
