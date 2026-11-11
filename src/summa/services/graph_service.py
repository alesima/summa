"""Helpers to keep the knowledge graph in sync with financial data."""
from __future__ import annotations

import re
from typing import Optional

from .. import repo


def normalize_merchant(description: str) -> str:
    """Strip trailing dates/numbers to collapse repeated merchants."""
    d = (description or "").strip()
    d = re.sub(r"\s+\d{1,2}[\/\.\-]\d{1,2}(?:[\/\.\-]\d{2,4})?\s*$", "", d)
    return " ".join(d.split())


def sync_from_data() -> dict:
    """Populate graph triples from accounts, categories and transactions."""
    counts = {"accounts": 0, "merchants": 0, "categories": 0}
    for acc in repo.list_accounts():
        repo.add_triple("user", "has_account", acc["name"])
        counts["accounts"] += 1
    seen = set()
    for t in repo.list_transactions(limit=100000):
        desc = normalize_merchant(t.get("description") or "")
        cat = t.get("category_name")
        if desc and cat:
            key = (desc, cat)
            if key not in seen:
                seen.add(key)
                repo.add_triple(desc, "belongs_to", cat)
                counts["merchants"] += 1
    for c in repo.list_categories():
        repo.add_triple("user", "tracks", c["name"])
        counts["categories"] += 1
    return counts


def auto_add_transaction(description: str, category: Optional[str]) -> None:
    desc = normalize_merchant(description or "")
    if desc and category:
        try:
            repo.add_triple(desc, "belongs_to", category)
        except Exception:
            pass
