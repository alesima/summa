import os
from typer.testing import CliRunner
from summa.cli import app

runner = CliRunner()


def _env(tmp_path):
    d = tmp_path / "home"
    d.mkdir()
    os.environ["SUMMA_HOME"] = str(d)
    return d


def test_init_and_account(tmp_path):
    _env(tmp_path)
    r = runner.invoke(app, ["init"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["account", "add", "Nubank"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["account", "list"])
    assert "Nubank" in r.output


def test_tx_add_and_list(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["account", "add", "C"])
    r = runner.invoke(app, ["tx", "add", "10", "Cafe"])
    assert r.exit_code == 0
    assert "Cafe" in r.output
    r = runner.invoke(app, ["tx", "list"])
    assert "Cafe" in r.output
    assert "-10.00" in r.output


def test_tx_add_income(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["account", "add", "C"])
    r = runner.invoke(app, ["tx", "add", "100", "Salario", "--income"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["tx", "list"])
    assert "100.00" in r.output


def test_tx_import_dry_run(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["account", "add", "C"])
    csvp = tmp_path / "e.csv"
    csvp.write_text("Data;Descricao;Valor\n10/11/2026;Mercado;-50,00\n")
    r = runner.invoke(app, ["tx", "import", str(csvp), "--dry-run"])
    assert r.exit_code == 0
    assert "Mercado" in r.output


def test_tx_import_real(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["account", "add", "C"])
    csvp = tmp_path / "e.csv"
    csvp.write_text("Data;Descricao;Valor\n10/11/2026;Mercado;-50,00\n")
    r = runner.invoke(app, ["tx", "import", str(csvp)])
    assert r.exit_code == 0
    r = runner.invoke(app, ["tx", "list"])
    assert "Mercado" in r.output


def test_report_monthly(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["account", "add", "C"])
    runner.invoke(app, ["tx", "add", "10", "Cafe"])
    # month arg required
    from datetime import date
    r = runner.invoke(app, ["report", "monthly", date.today().strftime("%Y-%m")])
    assert r.exit_code == 0


def test_budget(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    r = runner.invoke(app, ["budget", "set", "Alimentação", "2026-11", "500"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["budget", "show", "2026-11"])
    assert r.exit_code == 0
    assert "Alimentação" in r.output


def test_ask_without_key(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["account", "add", "C"])
    r = runner.invoke(app, ["ask", "quanto gastei?"])
    # should fail gracefully with non-zero? our ask exits 1 on error
    assert r.exit_code != 0 or "Erro" in r.output


def test_category_list(tmp_path):
    _env(tmp_path)
    runner.invoke(app, ["init"])
    r = runner.invoke(app, ["category", "list"])
    assert r.exit_code == 0
    assert "Alimentação" in r.output
