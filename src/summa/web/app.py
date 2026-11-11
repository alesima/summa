"""FastAPI web application for summa."""
from __future__ import annotations

import csv
import io
import os
import tempfile
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import db, repo, models, importers, ai
from ..i18n import get_language, language_name

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="summa", description="Terminal personal finance tracker with AI — Web UI")


@app.on_event("startup")
def _startup():
    db.init()


def _ctx(request: Request, **kw):
    return {"request": request, "lang": get_language(), "lang_name": language_name(get_language()), **kw}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, month: str = None):
    db.init()
    if not month:
        month = date.today().strftime("%Y-%m")
    accounts = repo.list_accounts()
    mt = repo.monthly_totals(month)
    txns = repo.list_transactions(limit=15)
    budgets = repo.budget_status(month)
    cats = repo.list_categories()
    return templates.TemplateResponse(request, "index.html", _ctx(
        request, month=month, accounts=accounts, mt=mt, txns=txns, budgets=budgets, cats=cats,
        from_cents=models.from_cents,
    ))


@app.get("/transactions", response_class=HTMLResponse)
def transactions(request: Request, account: str = None, start: str = None, end: str = None, limit: int = 100):
    db.init()
    rows = repo.list_transactions(account=account, start=start, end=end, limit=limit)
    accounts = repo.list_accounts()
    cats = repo.list_categories()
    return templates.TemplateResponse(request, "transactions.html", _ctx(
        request, rows=rows, accounts=accounts, cats=cats, account=account, start=start, end=end,
        from_cents=models.from_cents,
    ))


@app.post("/transactions/add")
def add_transaction(
    amount: float = Form(...),
    description: str = Form(...),
    account: str = Form(None),
    date_str: str = Form(None),
    category: str = Form(None),
    income: bool = Form(False),
):
    db.init()
    accounts = repo.list_accounts()
    acc = repo.get_account(account) if account else (accounts[0] if accounts else None)
    if not acc:
        return RedirectResponse("/transactions", status_code=303)
    d = date_str or date.today().isoformat()
    cents = models.to_cents(amount)
    cents = abs(cents) if income else -abs(cents)
    cat_id = None
    if category:
        cat = repo.get_category(category)
        if cat:
            cat_id = cat["id"]
    tx = models.Transaction(
        account_id=acc["id"], date=date.fromisoformat(d), amount_cents=cents,
        description=description, category_id=cat_id,
    )
    repo.add_transaction(tx)
    return RedirectResponse("/transactions", status_code=303)


@app.get("/import", response_class=HTMLResponse)
def import_form(request: Request):
    db.init()
    accounts = repo.list_accounts()
    return templates.TemplateResponse(request, "import.html", _ctx(request, accounts=accounts))


@app.post("/import")
async def do_import(request: Request, file: UploadFile = File(...), account: str = Form(None), categorize: bool = Form(False)):
    db.init()
    accounts = repo.list_accounts()
    acc = repo.get_account(account) if account else (accounts[0] if len(accounts) == 1 else None)
    if not acc:
        return RedirectResponse("/import", status_code=303)
    # save uploaded file
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        from ..services.import_service import import_statement
        result = import_statement(tmp_path, account_name=acc["name"], categorize=categorize)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    return templates.TemplateResponse(request, "import_result.html", _ctx(request, result=result, filename=file.filename))


@app.get("/ask", response_class=HTMLResponse)
def ask_form(request: Request):
    db.init()
    return templates.TemplateResponse(request, "ask.html", _ctx(request))


@app.post("/ask", response_class=HTMLResponse)
def ask_submit(request: Request, question: str = Form(...)):
    db.init()
    txns = repo.list_transactions(limit=200)
    lines = [f"{t['date']} | {t['description']} | {t['category_name'] or '-'} | {t['amount_cents']/100.0:.2f}" for t in txns]
    context = "Transactions:\n" + "\n".join(lines)
    from datetime import date as _d
    today = _d.today()
    months = []
    for i in range(6):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12; y -= 1
        months.append(f"{y:04d}-{m:02d}")
    mt_lines = []
    for mm in months:
        mt = repo.monthly_totals(mm)
        mt_lines.append(f"{mm}: income R$ {mt['income_cents']/100.0:.2f}, expenses R$ {abs(mt['expense_cents'])/100.0:.2f}")
    context += "\n\nMonthly totals:\n" + "\n".join(mt_lines)
    mem = repo.memories_as_context()
    graph = repo.graph_as_context()
    extra = "\n\n".join(x for x in (mem, graph) if x)
    if extra:
        context += "\n\n" + extra
    try:
        answer = ai.answer_question(question, context)
    except Exception as e:
        answer = f"Error: {e}"
    return templates.TemplateResponse(request, "ask.html", _ctx(request, question=question, answer=answer))


@app.get("/budgets", response_class=HTMLResponse)
def budgets(request: Request, month: str = None):
    db.init()
    if not month:
        month = date.today().strftime("%Y-%m")
    rows = repo.budget_status(month)
    return templates.TemplateResponse(request, "budgets.html", _ctx(request, month=month, rows=rows, from_cents=models.from_cents))


def run_web(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)
