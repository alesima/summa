import os
import tempfile
from pathlib import Path

import pytest

from summa import db, repo


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    d = tmp_path / "summa_home"
    d.mkdir()
    monkeypatch.setenv("SUMMA_HOME", str(d))
    # ensure fresh
    dbp = d / "summa.db"
    if dbp.exists():
        dbp.unlink()
    return d


@pytest.fixture
def initialized(tmp_data_dir):
    db.init()
    return tmp_data_dir


@pytest.fixture
def account(initialized):
    aid = repo.add_account(__import__("summa.models", fromlist=["Account"]).Account(name="Conta Teste"))
    return aid
