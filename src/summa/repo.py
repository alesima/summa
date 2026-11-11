"""Data access repositories."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from .db import db
from . import db as dbmod
from .models import Account, Category, Transaction, Budget


# ---------- Accounts ----------
def add_account(acc: Account) -> int:
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO accounts(name, type, currency) VALUES (?,?,?)",
            (acc.name, acc.type, acc.currency),
        )
        return cur.lastrowid


def list_accounts() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def get_account(name_or_id) -> Optional[dict]:
    with db() as conn:
        if isinstance(name_or_id, int):
            row = conn.execute("SELECT * FROM accounts WHERE id=?", (name_or_id,)).fetchone()
        else:
            # try id then name
            try:
                aid = int(name_or_id)
                row = conn.execute("SELECT * FROM accounts WHERE id=?", (aid,)).fetchone()
            except (ValueError, TypeError):
                row = conn.execute("SELECT * FROM accounts WHERE name=?", (name_or_id,)).fetchone()
        return dict(row) if row else None


def delete_account(name_or_id) -> bool:
    acc = get_account(name_or_id)
    if not acc:
        return False
    with db() as conn:
        conn.execute("DELETE FROM accounts WHERE id=?", (acc["id"],))
    return True


# ---------- Categories ----------
def list_categories(kind: Optional[str] = None) -> list[dict]:
    with db() as conn:
        if kind:
            rows = conn.execute("SELECT * FROM categories WHERE kind=? ORDER BY name", (kind,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM categories ORDER BY kind, name").fetchall()
        return [dict(r) for r in rows]


def get_category(name_or_id) -> Optional[dict]:
    with db() as conn:
        try:
            cid = int(name_or_id)
            row = conn.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
        except (ValueError, TypeError):
            row = conn.execute("SELECT * FROM categories WHERE name=?", (name_or_id,)).fetchone()
        return dict(row) if row else None


def add_category(cat: Category) -> int:
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO categories(name, kind, parent_id) VALUES (?,?,?)",
            (cat.name, cat.kind, cat.parent_id),
        )
        return cur.lastrowid


# ---------- Transactions ----------
def add_transaction(tx: Transaction) -> int:
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO transactions(account_id, date, amount_cents, description, category_id, notes, raw)
               VALUES (?,?,?,?,?,?,?)""",
            (tx.account_id, tx.date.isoformat(), tx.amount_cents, tx.description,
             tx.category_id, tx.notes, tx.raw),
        )
        return cur.lastrowid


def list_transactions(
    account: Optional[str] = None,
    category: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    uncategorized: bool = False,
    limit: int = 100,
) -> list[dict]:
    q = """SELECT t.*, a.name AS account_name, c.name AS category_name
           FROM transactions t JOIN accounts a ON a.id=t.account_id
           LEFT JOIN categories c ON c.id=t.category_id WHERE 1=1"""
    params: list = []
    if account:
        acc = get_account(account)
        if acc:
            q += " AND t.account_id=?"; params.append(acc["id"])
    if category:
        cat = get_category(category)
        if cat:
            q += " AND t.category_id=?"; params.append(cat["id"])
    if start:
        q += " AND t.date>=?"; params.append(start)
    if end:
        q += " AND t.date<=?"; params.append(end)
    if uncategorized:
        q += " AND t.category_id IS NULL"
    q += " ORDER BY t.date DESC, t.id DESC LIMIT ?"
    params.append(limit)
    with db() as conn:
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def update_transaction_category(tx_id: int, category_id: Optional[int]) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE transactions SET category_id=?, updated_at=datetime('now') WHERE id=?",
            (category_id, tx_id),
        )


def delete_transaction(tx_id: int) -> bool:
    with db() as conn:
        cur = conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
        return cur.rowcount > 0


def summary_by_category(start: Optional[str] = None, end: Optional[str] = None) -> list[dict]:
    q = """SELECT c.name AS category, c.kind, COALESCE(SUM(t.amount_cents),0) AS total_cents, COUNT(*) AS n
           FROM transactions t LEFT JOIN categories c ON c.id=t.category_id
           WHERE 1=1"""
    params: list = []
    if start:
        q += " AND t.date>=?"; params.append(start)
    if end:
        q += " AND t.date<=?"; params.append(end)
    q += " GROUP BY c.id ORDER BY total_cents ASC"
    with db() as conn:
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def monthly_totals(month: str) -> dict:
    # month YYYY-MM
    start = month + "-01"
    # end last day
    y, m = month.split("-")
    import calendar
    last = calendar.monthrange(int(y), int(m))[1]
    end = f"{month}-{last:02d}"
    with db() as conn:
        income = conn.execute(
            """SELECT COALESCE(SUM(t.amount_cents),0) FROM transactions t
               LEFT JOIN categories c ON c.id=t.category_id
               WHERE t.date>=? AND t.date<=? AND t.amount_cents>0
               AND COALESCE(c.kind,'expense')!='transfer'""",
            (start, end),
        ).fetchone()[0]
        expense = conn.execute(
            """SELECT COALESCE(SUM(t.amount_cents),0) FROM transactions t
               LEFT JOIN categories c ON c.id=t.category_id
               WHERE t.date>=? AND t.date<=? AND t.amount_cents<0
               AND COALESCE(c.kind,'expense')!='transfer'""",
            (start, end),
        ).fetchone()[0]
        count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE date>=? AND date<=?", (start, end)
        ).fetchone()[0]
    return {"month": month, "income_cents": income, "expense_cents": expense, "count": count}


# ---------- Budgets ----------
def set_budget(category_id: int, month: str, amount_cents: int) -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO budgets(category_id, month, amount_cents) VALUES (?,?,?)
               ON CONFLICT(category_id, month) DO UPDATE SET amount_cents=excluded.amount_cents""",
            (category_id, month, amount_cents),
        )


def list_budgets(month: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """SELECT b.*, c.name AS category_name FROM budgets b
               JOIN categories c ON c.id=b.category_id WHERE b.month=? ORDER BY c.name""",
            (month,),
        ).fetchall()
        return [dict(r) for r in rows]


def budget_status(month: str) -> list[dict]:
    # spent per category vs budget
    y, m = month.split("-")
    import calendar
    last = calendar.monthrange(int(y), int(m))[1]
    start = f"{month}-01"
    end = f"{month}-{last:02d}"
    with db() as conn:
        rows = conn.execute(
            """SELECT c.id AS category_id, c.name AS category,
                      COALESCE(b.amount_cents,0) AS budget_cents,
                      COALESCE(SUM(CASE WHEN t.amount_cents<0 THEN -t.amount_cents ELSE 0 END),0) AS spent_cents
               FROM categories c
               LEFT JOIN budgets b ON b.category_id=c.id AND b.month=?
               LEFT JOIN transactions t ON t.category_id=c.id AND t.date>=? AND t.date<=?
               WHERE c.kind='expense'
               GROUP BY c.id ORDER BY c.name""",
            (month, start, end),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Imported documents (dedup) ----------
def find_imported_document(file_hash: str, account_id: int) -> Optional[dict]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM imported_documents WHERE file_hash=? AND account_id=?",
            (file_hash, account_id),
        ).fetchone()
        return dict(row) if row else None


def record_imported_document(file_hash: str, filename: str, account_id: int, count: int) -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO imported_documents(file_hash, filename, account_id, transactions_count)
               VALUES (?,?,?,?)
               ON CONFLICT(file_hash, account_id) DO UPDATE SET
                   transactions_count=excluded.transactions_count,
                   imported_at=datetime('now')""",
            (file_hash, filename, account_id, count),
        )


# ---------- Memories ----------
def add_memory(key: str, value: str, scope: str = "global") -> int:
    dbmod.init()
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO memories(key, value, scope) VALUES (?,?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, scope=excluded.scope, updated_at=datetime('now')""",
            (key, value, scope),
        )
        return cur.lastrowid


def list_memories(scope: Optional[str] = None) -> list[dict]:
    try:
        with db() as conn:
            if scope:
                rows = conn.execute("SELECT * FROM memories WHERE scope=? ORDER BY key", (scope,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM memories ORDER BY key").fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_memory(key: str) -> Optional[dict]:
    with db() as conn:
        row = conn.execute("SELECT * FROM memories WHERE key=?", (key,)).fetchone()
        return dict(row) if row else None


def delete_memory(key: str) -> bool:
    dbmod.init()
    with db() as conn:
        cur = conn.execute("DELETE FROM memories WHERE key=?", (key,))
        return cur.rowcount > 0


def memories_as_context() -> str:
    rows = list_memories()
    if not rows:
        return ""
    lines = [f"- {r['key']}: {r['value']}" for r in rows]
    return "User memories/notes:\n" + "\n".join(lines)


# ---------- Knowledge graph (triples) ----------
def add_triple(subject: str, predicate: str, object_: str, confidence: float = 1.0) -> int:
    dbmod.init()
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO graph_triples(subject, predicate, object, confidence) VALUES (?,?,?,?)
               ON CONFLICT(subject, predicate, object) DO UPDATE SET confidence=excluded.confidence""",
            (subject, predicate, object_, confidence),
        )
        return cur.lastrowid


def list_triples(subject: Optional[str] = None, predicate: Optional[str] = None,
                 object_: Optional[str] = None) -> list[dict]:
    try:
        with db() as conn:
            q = "SELECT * FROM graph_triples WHERE 1=1"
            params = []
            if subject:
                q += " AND subject=?"; params.append(subject)
            if predicate:
                q += " AND predicate=?"; params.append(predicate)
            if object_:
                q += " AND object=?"; params.append(object_)
            q += " ORDER BY subject, predicate"
            rows = conn.execute(q, params).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def delete_triple(subject: str, predicate: str, object_: str) -> bool:
    dbmod.init()
    with db() as conn:
        cur = conn.execute(
            "DELETE FROM graph_triples WHERE subject=? AND predicate=? AND object=?",
            (subject, predicate, object_),
        )
        return cur.rowcount > 0


def graph_as_context(subject: Optional[str] = None) -> str:
    rows = list_triples(subject=subject)
    if not rows:
        return ""
    lines = [f"- {r['subject']} {r['predicate']} {r['object']} (conf {r['confidence']:.2f})" for r in rows]
    return "Knowledge graph:\n" + "\n".join(lines)


# ---------- Merchant aliases ----------
def add_alias(raw: str, clean: str) -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO merchant_aliases(raw, clean) VALUES (?,?)
               ON CONFLICT(raw) DO UPDATE SET clean=excluded.clean""",
            (raw, clean),
        )


def list_aliases() -> list[dict]:
    try:
        with db() as conn:
            rows = conn.execute("SELECT * FROM merchant_aliases ORDER BY raw").fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def delete_alias(raw: str) -> bool:
    dbmod.init()
    with db() as conn:
        cur = conn.execute("DELETE FROM merchant_aliases WHERE raw=?", (raw,))
        return cur.rowcount > 0


def resolve_alias(description: str) -> Optional[str]:
    """Return cleaned name if an alias exists, else None."""
    try:
        with db() as conn:
            row = conn.execute("SELECT clean FROM merchant_aliases WHERE raw=?", (description,)).fetchone()
            if row:
                return row["clean"]
            # try normalized raw
            row = conn.execute("SELECT clean FROM merchant_aliases WHERE raw=?", (description.strip(),)).fetchone()
            if row:
                return row["clean"]
    except Exception:
        pass
    return None
