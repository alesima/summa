"""Bank statement importers (CSV, OFX)."""
from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d",
    "%d/%m/%y", "%m/%d/%y",
]


def _parse_date(s: str) -> Optional[str]:
    s = s.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    # try OFX style YYYYMMDD
    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", s)
    if m:
        y, mo, d = m.groups()
        try:
            return datetime(int(y), int(mo), int(d)).date().isoformat()
        except ValueError:
            pass
    return None


def _to_float(s: str) -> Optional[float]:
    s = s.strip().replace("R$", "").replace(" ", "")
    # handle Brazilian decimal: 1.234,56 -> 1234.56
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    s = s.replace("+", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_csv(path: Path) -> list[dict]:
    rows_out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(2048)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
        except Exception:
            dialect = csv.excel
        reader = csv.reader(f, dialect)
        rows = list(reader)
    if not rows:
        return []
    # find header
    header = [h.strip().lower() for h in rows[0]]
    # map columns
    date_idx = desc_idx = amt_idx = debit_idx = credit_idx = None
    for i, h in enumerate(header):
        if any(k in h for k in ("data", "date", "dt")):
            date_idx = i
        if any(k in h for k in ("descri", "histórico", "historico", "memo", "title", "lançamento", "lancamento", "estabelecimento")):
            desc_idx = i
        if any(k in h for k in ("valor", "amount", "value", "montante")):
            amt_idx = i
        if any(k in h for k in ("débito", "debito", "debit", "saída", "saida")):
            debit_idx = i
        if any(k in h for k in ("crédito", "credito", "credit", "entrada")):
            credit_idx = i
    # if no header detected, assume first row data with positions 0,1,2
    data_rows = rows[1:] if (date_idx is not None or amt_idx is not None) else rows
    if date_idx is None:
        date_idx = 0
    if desc_idx is None:
        desc_idx = 1 if len(rows[0]) > 1 else 0
    if amt_idx is None and debit_idx is None and credit_idx is None:
        amt_idx = 2 if len(rows[0]) > 2 else None

    for r in data_rows:
        if not r or all(c.strip() == "" for c in r):
            continue
        if len(r) <= max(date_idx, desc_idx):
            continue
        d = _parse_date(r[date_idx])
        if not d:
            continue
        desc = r[desc_idx].strip() if desc_idx < len(r) else ""
        amount = None
        if amt_idx is not None and amt_idx < len(r):
            amount = _to_float(r[amt_idx])
        if amount is None and (debit_idx is not None or credit_idx is not None):
            deb = _to_float(r[debit_idx]) if (debit_idx is not None and debit_idx < len(r)) else None
            cred = _to_float(r[credit_idx]) if (credit_idx is not None and credit_idx < len(r)) else None
            if deb is not None and deb != 0:
                amount = -abs(deb)
            elif cred is not None and cred != 0:
                amount = abs(cred)
        if amount is None:
            continue
        rows_out.append({
            "date": d,
            "description": desc or "(no description)",
            "amount": amount,
            "raw": ",".join(r),
        })
    return rows_out


def parse_ofx(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    # detect currency
    cur_match = re.search(r"<CURDEF>([A-Z]{3})", text, re.I)
    currency = cur_match.group(1).upper() if cur_match else None
    # find STMTTRN blocks
    out = []
    for m in re.finditer(r"<STMTTRN>(.*?)</STMTTRN>", text, re.S | re.I):
        block = m.group(1)
        def get(tag):
            mm = re.search(rf"<{tag}>([^<\r\n]+)", block, re.I)
            return mm.group(1).strip() if mm else None
        dt = get("DTPOSTED") or get("DTUSER")
        amt = get("TRNAMT")
        memo = get("MEMO") or get("NAME") or ""
        if dt is None or amt is None:
            continue
        d = _parse_date(dt)
        if not d:
            continue
        a = _to_float(amt)
        if a is None:
            continue
        row = {"date": d, "description": memo.strip() or "(no description)", "amount": a, "raw": block.strip()}
        if currency:
            row["currency"] = currency
        out.append(row)
    return out


def parse_statement(path: Path) -> list[dict]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".ofx", ".qfx"):
        return parse_ofx(path)
    # try csv first
    try:
        res = parse_csv(path)
        if res:
            return res
    except Exception:
        pass
    # fallback ofx
    try:
        return parse_ofx(path)
    except Exception:
        return []
