"""Configuration and paths for summa."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# load from cwd and from ~/.summa
load_dotenv()
load_dotenv(Path.home() / ".summa" / ".env")

APP_NAME = "summa"

def data_dir() -> Path:
    base = os.environ.get("SUMMA_HOME")
    if base:
        p = Path(base).expanduser()
    else:
        # XDG-ish: prefer ~/.summa
        p = Path.home() / ".summa"
    p.mkdir(parents=True, exist_ok=True)
    return p

def db_path() -> Path:
    return data_dir() / "summa.db"

def ai_provider() -> str:
    return os.environ.get("SUMMA_AI_PROVIDER", "").lower().strip()

def ai_model() -> str:
    return os.environ.get("SUMMA_AI_MODEL", "").strip()

def openai_key() -> str | None:
    return os.environ.get("OPENAI_API_KEY")

def anthropic_key() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY")
