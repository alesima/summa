import json
from unittest.mock import patch

from summa import ai


def test_resolve_provider_none(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SUMMA_AI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("SUMMA_AI_PROVIDER", raising=False)
    assert ai.resolve_provider() == "none"


def test_resolve_provider_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.delenv("SUMMA_AI_PROVIDER", raising=False)
    assert ai.resolve_provider() == "openai"


def test_resolve_model_default(monkeypatch):
    monkeypatch.delenv("SUMMA_AI_MODEL", raising=False)
    assert ai.resolve_model("openai") == "gpt-5.6-terra"


def test_categorize_transactions_mock():
    fake = json.dumps({"items": [{"id": 1, "category": "Alimentação"}, {"id": 2, "category": "Transporte"}]})
    with patch("summa.ai.chat", return_value=fake):
        res = ai.categorize_transactions(
            [{"id": 1, "description": "Mercado", "amount_cents": -50, "date": "2026-11-10"},
             {"id": 2, "description": "Uber", "amount_cents": -20, "date": "2026-11-10"}],
            ["Alimentação", "Transporte"],
        )
    assert res == [{"id": 1, "category": "Alimentação"}, {"id": 2, "category": "Transporte"}]


def test_categorize_transactions_bad_json():
    with patch("summa.ai.chat", return_value="not json"):
        res = ai.categorize_transactions([{"id": 1, "description": "x", "amount_cents": 1, "date": "d"}], ["Outros"])
    assert res == []


def test_answer_question_mock():
    with patch("summa.ai.chat", return_value="Você gastou R$ 50."):
        assert ai.answer_question("quanto?", "ctx") == "Você gastou R$ 50."


def test_chat_openai_mock(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.delenv("SUMMA_AI_MODEL", raising=False)
    # mock openai client
    class FakeMsg:
        content = "ok"
    class FakeChoice:
        message = FakeMsg()
    class FakeResp:
        choices = [FakeChoice()]
    class FakeCompletions:
        def create(self, **kw):
            return FakeResp()
    class FakeChat:
        completions = FakeCompletions()
    class FakeClient:
        chat = FakeChat()
    monkeypatch.setattr("openai.OpenAI", lambda **kw: FakeClient())
    assert ai.chat("sys", "usr") == "ok"
