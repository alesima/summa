"""SQLite storage layer."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL DEFAULT 'checking',
    currency TEXT NOT NULL DEFAULT 'BRL',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL DEFAULT 'expense',  -- expense | income
    parent_id INTEGER REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    date TEXT NOT NULL,            -- ISO YYYY-MM-DD
    amount_cents INTEGER NOT NULL,  -- positive income, negative expense
    description TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    notes TEXT,
    raw TEXT,                      -- original imported line
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    month TEXT NOT NULL,           -- YYYY-MM
    amount_cents INTEGER NOT NULL,
    UNIQUE(category_id, month)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category_id);

CREATE TABLE IF NOT EXISTS fx_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_currency TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    rate REAL NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(base_currency, quote_currency)
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'global',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS token_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS imported_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT NOT NULL,
    filename TEXT NOT NULL,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    transactions_count INTEGER NOT NULL DEFAULT 0,
    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(file_hash, account_id)
);
"""

DEFAULT_CATEGORIES = [
    ("Moradia", "expense"),
    ("Alimentação", "expense"),
    ("Transporte", "expense"),
    ("Saúde", "expense"),
    ("Educação", "expense"),
    ("Lazer", "expense"),
    ("Compras", "expense"),
    ("Assinaturas", "expense"),
    ("Contas/Serviços", "expense"),
    ("Outros", "expense"),
    ("Salário", "income"),
    ("Freelance", "income"),
    ("Investimentos", "income"),
    ("Outras receitas", "income"),
    ("Transferência", "transfer"),
]


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db(path: Path | None = None):
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init(path: Path | None = None) -> None:
    with db(path) as conn:
        conn.executescript(SCHEMA)
        # seed categories
        existing = {r[0] for r in conn.execute("SELECT name FROM categories").fetchall()}
        for name, kind in DEFAULT_CATEGORIES:
            if name not in existing:
                conn.execute(
                    "INSERT INTO categories(name, kind) VALUES (?, ?)", (name, kind)
                )
