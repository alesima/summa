from pathlib import Path
from summa import importers


def test_parse_csv_semicolon(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("Data;Descrição;Valor\n10/11/2026;Supermercado;-120,50\n09/11/2026;Farmacia;-35.00\n",
                 encoding="utf-8")
    rows = importers.parse_csv(p)
    assert len(rows) == 2
    assert rows[0]["description"] == "Supermercado"
    assert rows[0]["amount"] == -120.5
    assert rows[0]["date"] == "2026-11-10"


def test_parse_csv_debit_credit(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("data,descricao,debito,credito\n10/11/2026,Mercado,50.00,\n09/11/2026,Salario,,1000.00\n",
                 encoding="utf-8")
    rows = importers.parse_csv(p)
    assert len(rows) == 2
    assert rows[0]["amount"] == -50.0
    assert rows[1]["amount"] == 1000.0


def test_parse_csv_empty(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("", encoding="utf-8")
    assert importers.parse_csv(p) == []


def test_parse_ofx(tmp_path):
    p = tmp_path / "e.ofx"
    p.write_text("""<OFX>
<STMTTRN>
<DTPOSTED>20261110
<TRNAMT>-89.90
<MEMO>Restaurante
</STMTTRN>
<STMTTRN>
<DTPOSTED>20261109
<TRNAMT>2000.00
<MEMO>Freelance
</STMTTRN>
</OFX>""", encoding="utf-8")
    rows = importers.parse_ofx(p)
    assert len(rows) == 2
    assert rows[0]["amount"] == -89.9
    assert rows[1]["amount"] == 2000.0


def test_parse_statement_auto(tmp_path):
    p = tmp_path / "e.ofx"
    p.write_text("<STMTTRN><DTPOSTED>20261110<TRNAMT>-10<MEMO>X</STMTTRN>", encoding="utf-8")
    rows = importers.parse_statement(p)
    assert len(rows) == 1


def test_parse_date_formats():
    assert importers._parse_date("2026-11-10") == "2026-11-10"
    assert importers._parse_date("10/11/2026") == "2026-11-10"
    assert importers._parse_date("20261110") == "2026-11-10"
    assert importers._parse_date("nope") is None


def test_to_float_brl():
    assert importers._to_float("1.234,56") == 1234.56
    assert importers._to_float("-35.00") == -35.0
