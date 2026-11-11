import os
import csv
from typer.testing import CliRunner
from summa.cli import app

runner = CliRunner()


def _env(tmp_path):
    d = tmp_path / "home"
    d.mkdir()
    os.environ["SUMMA_HOME"] = str(d)
    return d


def test_lang_set_and_get(tmp_path):
    _env(tmp_path)
    r = runner.invoke(app, ["init"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["lang", "en"])
    assert r.exit_code == 0
    assert "en" in r.output.lower()
    r = runner.invoke(app, ["lang"])
    assert "en" in r.output


def test_lang_invalid(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    r = runner.invoke(app, ["lang", "xx-YY"])
    assert r.exit_code != 0


def test_export_csv(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["account", "add", "C"])
    runner.invoke(app, ["tx", "add", "10", "Coffee"])
    out = tmp_path / "out.csv"
    r = runner.invoke(app, ["export", str(out)])
    assert r.exit_code == 0
    assert out.exists()
    with open(out) as f:
        rows = list(csv.reader(f))
    assert rows[0][0] == "id"
    assert len(rows) == 2
    assert rows[1][3] == "Coffee"


def test_fx_set_and_list(tmp_path):
    _env(tmp_path)
    r = runner.invoke(app, ["init"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["fx", "set", "USD", "BRL", "5.20"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["fx", "list"])
    assert r.exit_code == 0
    assert "USD" in r.output
    assert "BRL" in r.output


def test_chart_spending_empty(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    r = runner.invoke(app, ["chart", "spending"])
    assert r.exit_code == 0


def test_chart_trend(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    r = runner.invoke(app, ["chart", "trend", "--months", "3"])
    assert r.exit_code == 0


def test_import_dedup_and_transfer(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    # create a credit card account and a checking account
    runner.invoke(app, ["account", "add", "Card", "--type", "credit"])
    runner.invoke(app, ["account", "add", "Checking"])
    # import checking statement with a card payment
    csvp = tmp_path / "checking.csv"
    csvp.write_text("Data;Descricao;Valor\n10/11/2026;Pagamento cartao Card;-200.00\n09/11/2026;Mercado;-50.00\n")
    r = runner.invoke(app, ["tx", "import", str(csvp), "--account", "Checking"])
    assert r.exit_code == 0
    # import again -> dedup skips both
    r = runner.invoke(app, ["tx", "import", str(csvp), "--account", "Checking"])
    assert r.exit_code == 0
    assert "Skipped 2" in r.output
    # the payment should be categorized as transfer
    r = runner.invoke(app, ["tx", "list", "--account", "Checking"])
    assert "Transfer" in r.output or "Transferência" in r.output
