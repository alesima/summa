from summa import db


def test_init_creates_tables(tmp_data_dir):
    db.init()
    with db.db() as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "accounts" in tables
    assert "transactions" in tables
    assert "categories" in tables


def test_init_seeds_categories(tmp_data_dir):
    db.init()
    with db.db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    assert n >= 10


def test_init_idempotent(tmp_data_dir):
    db.init()
    db.init()
    with db.db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    assert n >= 10
