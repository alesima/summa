import os
from unittest.mock import patch

from summa.services import decision_service


def test_backend_default_llm(monkeypatch):
    monkeypatch.delenv("SUMMA_DECISION_PROVIDER", raising=False)
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    assert decision_service.backend_name() == "auto"
    m = decision_service.get_decision_model()
    assert m.__class__.__name__ == "LLMDecisionModel"


def test_backend_jev_selected(monkeypatch):
    monkeypatch.setenv("SUMMA_DECISION_PROVIDER", "jev")
    monkeypatch.setenv("JEV_API_KEY", "x")
    m = decision_service.get_decision_model()
    assert m.__class__.__name__ == "JEVDecisionModel"


def test_categorize_fallback(monkeypatch):
    monkeypatch.setenv("SUMMA_DECISION_PROVIDER", "jev")
    monkeypatch.setenv("JEV_API_KEY", "x")
    # make JEV fail
    with patch("summa.adapters.jev.JEVDecisionModel.categorize", side_effect=RuntimeError("boom")):
        with patch("summa.adapters.llm_decision.LLMDecisionModel.categorize", return_value=[{"id": 1, "category": "Outros", "confidence": 1.0}]):
            res = decision_service.categorize([{"id": 1, "description": "x", "amount_cents": 1, "date": "d"}], ["Outros"])
    assert res[0]["category"] == "Outros"
