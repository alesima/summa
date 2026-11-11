"""AI integration (OpenAI / Anthropic)."""
from __future__ import annotations

import json
import os
from typing import Optional

from .config import ai_provider, ai_model, openai_key, anthropic_key
from .i18n import get_language, language_name


def resolve_provider() -> str:
    p = ai_provider()
    if p in ("openai", "anthropic"):
        return p
    # auto-detect
    if openai_key() or os.environ.get("SUMMA_AI_BASE_URL") or os.environ.get("OPENAI_BASE_URL"):
        return "openai"
    if anthropic_key():
        return "anthropic"
    return "none"


def resolve_model(provider: str) -> str:
    m = ai_model()
    if m:
        return m
    if provider == "openai":
        return "o4-mini"
    if provider == "anthropic":
        return "claude-haiku-4-5-20251001"
    return ""


def openai_base_url() -> str | None:
    return os.environ.get("SUMMA_AI_BASE_URL") or os.environ.get("OPENAI_BASE_URL")


def chat(system: str, user: str, *, json_mode: bool = False) -> str:
    provider = resolve_provider()
    model = resolve_model(provider)
    if provider == "none":
        raise RuntimeError(
            "Nenhuma API key configurada. Defina OPENAI_API_KEY ou ANTHROPIC_API_KEY (e opcionalmente SUMMA_AI_MODEL/SUMMA_AI_PROVIDER)."
        )
    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=openai_key() or "ollama", base_url=openai_base_url())
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_key())
        resp = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        out = []
        for b in resp.content:
            if getattr(b, "text", None):
                out.append(b.text)
        return "\n".join(out)
    raise RuntimeError(f"Provider desconhecido: {provider}")


def categorize_transactions(txns: list[dict], categories: list[str]) -> list[dict]:
    """Return list of {id, category} suggestions."""
    if not txns:
        return []
    lang = language_name(get_language())
    system = (
        "You are a personal finance assistant. Given a list of transactions and a list of categories, "
        "suggest the most appropriate category for each transaction. Reply ONLY with valid JSON in the format: "
        '{"items": [{"id": <int>, "category": "<exact name from the list>"}]}. '
        "Use exactly the names from the category list. If unsure, use 'Outros'. "
        f"Respond in {lang}."
    )
    payload = {
        "categories": categories,
        "transactions": [
            {"id": t["id"], "description": t["description"], "amount_cents": t["amount_cents"], "date": t["date"]}
            for t in txns
        ],
    }
    user = json.dumps(payload, ensure_ascii=False)
    raw = chat(system, user, json_mode=True)
    try:
        data = json.loads(raw)
        return data.get("items", [])
    except json.JSONDecodeError:
        # try to extract json
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            try:
                data = json.loads(raw[start:end+1])
                return data.get("items", [])
            except Exception:
                return []
        return []


def answer_question(question: str, context: str) -> str:
    lang = language_name(get_language())
    system = (
        "You are a personal finance assistant. Answer the user's question based on the provided data. "
        "Be concise, use currency values (R$), and indicate when there is not enough data. "
        "Do not invent numbers. "
        f"Respond in {lang}."
    )
    user = f"Question: {question}\n\nData:\n{context}"
    return chat(system, user)
