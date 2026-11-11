"""Bank statement import business logic."""
from __future__ import annotations

from datetime import date
from typing import Optional

from .. import db, repo, models, importers, ai


PAYMENT_KEYWORDS = ("pagamento", "payment", "fatura", "cartao", "cartão", "card")


def is_transfer(acc: dict, parsed: dict, card_names: list[str]) -> bool:
    desc_l = (parsed.get("description") or "").lower()
    amt = parsed.get("amount", 0)
    if acc["type"] == "credit" and amt > 0:
        return True
    if acc["type"] != "credit":
        if any(kw in desc_l for kw in PAYMENT_KEYWORDS):
            return True
        if any(cn in desc_l for cn in card_names):
            return True
    return False


def import_statement(file, account_name: Optional[str] = None, *,
                    dry_run: bool = False, categorize: bool = False) -> dict:
    """Import a parsed statement into an account. Returns a summary dict."""
    db.init()
    accounts = repo.list_accounts()
    if not accounts:
        raise ValueError("No accounts exist. Create one first.")
    acc = repo.get_account(account_name) if account_name else (accounts[0] if len(accounts) == 1 else None)
    if not acc:
        raise ValueError("Account not specified and multiple accounts exist.")

    parsed = importers.parse_statement(file)
    if not parsed:
        return {"imported": 0, "skipped": 0, "parsed": 0, "account": acc["name"]}

    transfer_cat = repo.get_category("Transferência")
    transfer_cat_id = transfer_cat["id"] if transfer_cat else None
    card_names = [a["name"].lower() for a in accounts if a["type"] == "credit" and a["id"] != acc["id"]]

    n = 0
    skipped = 0
    for p in parsed:
        amt_cents = models.to_cents(p["amount"])
        existing = repo.list_transactions(account=acc["name"], start=p["date"], end=p["date"], limit=1000)
        dup = any(e["amount_cents"] == amt_cents and e["description"] == p["description"] for e in existing)
        if dup:
            skipped += 1
            continue
        cat_id = transfer_cat_id if (transfer_cat_id and is_transfer(acc, p, card_names)) else None
        tx = models.Transaction(
            account_id=acc["id"], date=date.fromisoformat(p["date"]),
            amount_cents=amt_cents, description=p["description"], raw=p["raw"],
            category_id=cat_id,
        )
        repo.add_transaction(tx)
        n += 1

    categorized = 0
    if categorize:
        txns = repo.list_transactions(uncategorized=True, limit=500)
        if txns:
            cats = list(dict.fromkeys([c["name"] for c in repo.list_categories()]))
            try:
                suggestions = ai.categorize_transactions(txns, cats)
                cat_by_name = {c["name"]: c["id"] for c in repo.list_categories()}
                for sug in suggestions:
                    cid = cat_by_name.get(sug.get("category"))
                    if cid is not None:
                        repo.update_transaction_category(sug["id"], cid)
                        categorized += 1
            except Exception:
                pass

    return {"imported": n, "skipped": skipped, "parsed": len(parsed),
            "categorized": categorized, "account": acc["name"], "parsed_rows": parsed}
