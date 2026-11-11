from summa import db, repo, models


def test_account_crud(initialized):
    aid = repo.add_account(models.Account(name="Nubank", type="checking"))
    assert aid > 0
    acc = repo.get_account("Nubank")
    assert acc["name"] == "Nubank"
    accs = repo.list_accounts()
    assert len(accs) == 1
    assert repo.delete_account("Nubank") is True
    assert repo.get_account("Nubank") is None


def test_account_duplicate_name(initialized):
    repo.add_account(models.Account(name="X"))
    import sqlite3
    try:
        repo.add_account(models.Account(name="X"))
        assert False, "should raise"
    except sqlite3.IntegrityError:
        pass


def test_transaction_add_and_list(initialized, account):
    tx = models.Transaction(account_id=account, date=__import__("datetime").date.today(),
                            amount_cents=-1000, description="Cafe")
    tid = repo.add_transaction(tx)
    assert tid > 0
    rows = repo.list_transactions()
    assert len(rows) == 1
    assert rows[0]["description"] == "Cafe"
    assert rows[0]["amount_cents"] == -1000


def test_transaction_filter_uncategorized(initialized, account):
    tx = models.Transaction(account_id=account, date=__import__("datetime").date.today(),
                            amount_cents=-500, description="X")
    repo.add_transaction(tx)
    unc = repo.list_transactions(uncategorized=True)
    assert len(unc) == 1


def test_category_update(initialized, account):
    cats = repo.list_categories()
    cid = cats[0]["id"]
    tx = models.Transaction(account_id=account, date=__import__("datetime").date.today(),
                            amount_cents=-500, description="X")
    tid = repo.add_transaction(tx)
    repo.update_transaction_category(tid, cid)
    rows = repo.list_transactions()
    assert rows[0]["category_id"] == cid


def test_delete_transaction(initialized, account):
    tx = models.Transaction(account_id=account, date=__import__("datetime").date.today(),
                            amount_cents=-500, description="X")
    tid = repo.add_transaction(tx)
    assert repo.delete_transaction(tid) is True
    assert repo.list_transactions() == []


def test_summary_by_category(initialized, account):
    cat = repo.get_category("Alimentação")
    tx = models.Transaction(account_id=account, date=__import__("datetime").date.today(),
                            amount_cents=-1200, description="Mercado", category_id=cat["id"])
    repo.add_transaction(tx)
    rows = repo.summary_by_category()
    assert any(r["category"] == "Alimentação" for r in rows)


def test_monthly_totals(initialized, account):
    from datetime import date
    today = date.today().isoformat()
    tx = models.Transaction(account_id=account, date=date.today(), amount_cents=1000, description="Sal")
    repo.add_transaction(tx)
    mt = repo.monthly_totals(date.today().strftime("%Y-%m"))
    assert mt["income_cents"] == 1000
    assert mt["count"] >= 1


def test_budget_set_and_status(initialized, account):
    cat = repo.get_category("Alimentação")
    repo.set_budget(cat["id"], "2026-11", 50000)
    bs = repo.list_budgets("2026-11")
    assert len(bs) == 1
    status = repo.budget_status("2026-11")
    assert any(r["category"] == "Alimentação" for r in status)


def test_budget_upsert(initialized):
    cat = repo.get_category("Alimentação")
    repo.set_budget(cat["id"], "2026-11", 10000)
    repo.set_budget(cat["id"], "2026-11", 20000)
    bs = repo.list_budgets("2026-11")
    assert bs[0]["amount_cents"] == 20000
