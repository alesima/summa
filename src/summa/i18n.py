"""Internationalization helpers.

The source code is in English. User-facing conversation language is
configurable (env SUMMA_LANGUAGE or `settings.language` in the DB).
"""
from __future__ import annotations

import os
from typing import Optional

from . import db

SUPPORTED = {
    "en": "English",
    "pt-BR": "Portuguese (Brazil)",
    "pt-PT": "Portuguese (Portugal)",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
}


def language_name(code: str) -> str:
    return SUPPORTED.get(code, code)


def get_language() -> str:
    # env takes precedence
    env = os.environ.get("SUMMA_LANGUAGE")
    if env:
        return env
    try:
        with db.db() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key='language'").fetchone()
            if row:
                return row[0]
    except Exception:
        pass
    return "pt-BR"


def set_language(code: str) -> None:
    if code not in SUPPORTED:
        raise ValueError(f"Unsupported language: {code}. Supported: {', '.join(SUPPORTED)}")
    with db.db() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES ('language', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (code,),
        )
    os.environ["SUMMA_LANGUAGE"] = code
