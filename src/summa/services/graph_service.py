"""Helpers to keep the knowledge graph in sync with financial data."""
from __future__ import annotations

import re
from typing import Optional

from .. import repo


# Common prefixes that indicate payment method, not merchant (BR bank statements).
DEFAULT_PREFIXES = [
    "PIX QRS", "PIX TRANSF", "PIX", "PAY", "PAG BOLETO", "PAGAMENTO", "PAG",
    "RSHOP", "RSCSS", "INT PRE-PAGO", "REND PAGO", "SALDO DO DIA",
]


def normalize_merchant(description: str) -> str:
    """Normalize a raw statement description into a merchant name.

    1. Check user-defined aliases.
    2. Strip common payment-method prefixes.
    3. Strip trailing date-like tokens.
    """
    d = (description or "").strip()
    if not d:
        return ""
    # strip known prefixes first
    upper = d.upper()
    for pref in sorted(DEFAULT_PREFIXES, key=len, reverse=True):
        if upper.startswith(pref + " ") or upper == pref:
            d = d[len(pref):].strip()
            upper = d.upper()
            break
    # strip trailing date-like tokens
    d = re.sub(r"\s+\d{1,2}[\/\.\-]\d{1,2}(?:[\/\.\-]\d{2,4})?\s*$", "", d)
    d = " ".join(d.split())
    # user alias (checked on normalized candidate and original)
    try:
        from .. import repo
        for cand in (d, (description or "").strip()):
            alias = repo.resolve_alias(cand)
            if alias:
                return alias
    except Exception:
        pass
    return d


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
