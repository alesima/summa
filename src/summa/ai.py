"""Provider-agnostic AI integration.

All providers are accessed through an OpenAI-compatible chat completions
interface. This keeps the code independent of any specific vendor SDK.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from .config import ai_provider, ai_model, openai_key, anthropic_key
from .i18n import get_language, language_name


def _base_url() -> Optional[str]:
    if os.environ.get("SUMMA_AI_BASE_URL") or os.environ.get("OPENAI_BASE_URL"):
        return os.environ.get("SUMMA_AI_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    provider = (ai_provider() or "").lower()
    if provider == "anthropic":
        return "https://api.anthropic.com/v1"
    return None


def _api_key() -> str:
    p = (ai_provider() or "").lower()
    if p == "anthropic":
        return anthropic_key() or openai_key() or "ollama"
    return openai_key() or anthropic_key() or "ollama"


def resolve_provider() -> str:
    p = (ai_provider() or "").lower()
    if p in ("openai", "anthropic", "ollama", "custom"):
        return p
    if openai_key() or os.environ.get("SUMMA_AI_BASE_URL") or os.environ.get("OPENAI_BASE_URL"):
        return "openai"
    if anthropic_key():
        return "anthropic"
    return "none"


def resolve_model(provider: str) -> str:
    m = ai_model()
    if m:
        return m
    if provider == "anthropic":
        return "claude-haiku-4-5-20251001"
    return "gpt-5.6-terra"


def _client():
    from openai import OpenAI
    return OpenAI(api_key=_api_key(), base_url=_base_url())


def chat(system: str, user: str, *, json_mode: bool = False) -> str:
    provider = resolve_provider()
    if provider == "none":
        raise RuntimeError(
            "No AI credentials configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY "
            "(or SUMMA_AI_BASE_URL for a local endpoint)."
        )
    model = resolve_model(provider)
    client = _client()
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:
        msg = str(e)
        low = msg.lower()
        # Some providers (e.g. Ollama) do not support response_format.
        if json_mode and "response_format" in low:
            kwargs.pop("response_format", None)
            resp = client.chat.completions.create(**kwargs)
        elif "404" in msg or "deprecated" in low or "does not exist" in low or "model_not_found" in low:
            raise RuntimeError(
                f"Model '{model}' is not available or deprecated. "
                "Update SUMMA_AI_MODEL (e.g. gpt-5.6-terra) or your provider's current model. "
                f"Original error: {msg}"
            )
        else:
            raise
    choice = resp.choices[0].message
    # record token usage (best-effort)
    try:
        usage = getattr(resp, "usage", None)
        if usage is not None:
            from . import db
            with db.db() as conn:
                conn.execute(
                    "INSERT INTO token_usage(model, prompt_tokens, completion_tokens, total_tokens) VALUES (?,?,?,?)",
                    (model,
                     getattr(usage, "prompt_tokens", 0) or 0,
                     getattr(usage, "completion_tokens", 0) or 0,
                     getattr(usage, "total_tokens", 0) or 0),
                )
    except Exception:
        pass
    return (choice.content if getattr(choice, "content", None) else "") or ""


def categorize_transactions(txns: list[dict], categories: list[str]) -> list[dict]:
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
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            try:
                data = json.loads(raw[start:end + 1])
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
