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
from .i18n import t as _t, available_languages
from ..i18n import get_language, language_name

templates.env.globals["t"] = _t
templates.env.globals["available_languages"] = available_languages


def _datefmt(value):
    if not value:
        return value
    try:
        from datetime import datetime
        return datetime.strptime(str(value), "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return value


templates.env.filters["datefmt"] = _datefmt

app = FastAPI(title="summa", description="Terminal personal finance tracker with AI — Web UI")


@app.on_event("startup")
def _startup():
    db.init()


def _ctx(request: Request, **kw):
    # prefer settings language
    try:
        with db.db() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key='language'").fetchone()
            if row:
                import os
                os.environ["SUMMA_LANGUAGE"] = row[0]
    except Exception:
        pass
    lang = get_language()
    return {"request": request, "lang": lang, "lang_name": language_name(lang), "t": _t, **kw}


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
    # chart data
    y, m = month.split("-")
    import calendar
    last = calendar.monthrange(int(y), int(m))[1]
    start = f"{month}-01"; end = f"{month}-{last:02d}"
    rows = repo.summary_by_category(start=start, end=end)
    chart_data = [{"category": r["category"] or "(uncategorized)", "total": abs(r["total_cents"])/100.0} for r in rows if (r["total_cents"] or 0) < 0]
    chart_data.sort(key=lambda x: x["total"], reverse=True)
    # trend data (6 months)
    from datetime import date as _d
    today = _d.today()
    trend_data = []
    for i in range(5, -1, -1):
        mm = today.month - i
        yy = today.year
        while mm <= 0:
            mm += 12; yy -= 1
        mstr = f"{yy:04d}-{mm:02d}"
        mt2 = repo.monthly_totals(mstr)
        trend_data.append({"month": mstr, "income": mt2["income_cents"]/100.0, "expense": abs(mt2["expense_cents"])/100.0})
    return templates.TemplateResponse(request, "index.html", _ctx(
        request, month=month, accounts=accounts, mt=mt, txns=txns, budgets=budgets, cats=cats,
        chart_data=chart_data, trend_data=trend_data,
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
    request: Request,
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
    if acc:
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
    # HTMX partial response
    if request.headers.get("HX-Request"):
        rows = repo.list_transactions(limit=15)
        return templates.TemplateResponse(request, "_transactions_table.html", {"request": request, "rows": rows})
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




@app.get("/accounts", response_class=HTMLResponse)
def accounts_page(request: Request):
    db.init()
    rows = repo.list_accounts()
    return templates.TemplateResponse(request, "accounts.html", _ctx(request, rows=rows))


@app.post("/accounts/add")
def accounts_add(name: str = Form(...), type: str = Form("checking"), currency: str = Form("BRL")):
    db.init()
    try:
        repo.add_account(models.Account(name=name, type=type, currency=currency))
    except Exception:
        pass
    return RedirectResponse("/accounts", status_code=303)


@app.post("/accounts/remove")
def accounts_remove(name: str = Form(...)):
    db.init()
    repo.delete_account(name)
    return RedirectResponse("/accounts", status_code=303)


@app.get("/categories", response_class=HTMLResponse)
def categories_page(request: Request):
    db.init()
    rows = repo.list_categories()
    return templates.TemplateResponse(request, "categories.html", _ctx(request, rows=rows))


@app.post("/categories/add")
def categories_add(name: str = Form(...), kind: str = Form("expense")):
    db.init()
    try:
        repo.add_category(models.Category(name=name, kind=kind))
    except Exception:
        pass
    return RedirectResponse("/categories", status_code=303)


@app.get("/memory", response_class=HTMLResponse)
def memory_page(request: Request):
    db.init()
    rows = repo.list_memories()
    return templates.TemplateResponse(request, "memory.html", _ctx(request, rows=rows))


@app.post("/memory/add")
def memory_add(key: str = Form(...), value: str = Form(...), scope: str = Form("global")):
    db.init()
    repo.add_memory(key, value, scope)
    return RedirectResponse("/memory", status_code=303)


@app.post("/memory/remove")
def memory_remove(key: str = Form(...)):
    db.init()
    repo.delete_memory(key)
    return RedirectResponse("/memory", status_code=303)


@app.get("/graph", response_class=HTMLResponse)
def graph_page(request: Request, subject: str = None, predicate: str = None):
    db.init()
    rows = repo.list_triples(subject=subject, predicate=predicate)
    return templates.TemplateResponse(request, "graph.html", _ctx(request, rows=rows, subject=subject, predicate=predicate))


@app.post("/graph/sync")
def graph_sync():
    db.init()
    from ..services.graph_service import sync_from_data
    sync_from_data()
    return RedirectResponse("/graph", status_code=303)


@app.post("/graph/clear")
def graph_clear():
    db.init()
    with db.db() as conn:
        conn.execute("DELETE FROM graph_triples")
    return RedirectResponse("/graph", status_code=303)


@app.get("/fx", response_class=HTMLResponse)
def fx_page(request: Request):
    db.init()
    with db.db() as conn:
        rows = conn.execute("SELECT * FROM fx_rates ORDER BY base_currency, quote_currency").fetchall()
    rows = [dict(r) for r in rows]
    return templates.TemplateResponse(request, "fx.html", _ctx(request, rows=rows))


@app.post("/fx/set")
def fx_set(base: str = Form(...), quote: str = Form(...), rate: float = Form(...)):
    db.init()
    with db.db() as conn:
        conn.execute(
            """INSERT INTO fx_rates(base_currency, quote_currency, rate) VALUES (?,?,?)
               ON CONFLICT(base_currency, quote_currency) DO UPDATE SET rate=excluded.rate, updated_at=datetime('now')""",
            (base.upper(), quote.upper(), rate),
        )
    return RedirectResponse("/fx", status_code=303)


@app.get("/usage", response_class=HTMLResponse)
def usage_page(request: Request):
    db.init()
    with db.db() as conn:
        rows = conn.execute("SELECT model, COALESCE(SUM(prompt_tokens),0) AS p, COALESCE(SUM(completion_tokens),0) AS c, COALESCE(SUM(total_tokens),0) AS t, COUNT(*) AS n FROM token_usage GROUP BY model").fetchall()
        tot = conn.execute("SELECT COALESCE(SUM(prompt_tokens),0), COALESCE(SUM(completion_tokens),0), COALESCE(SUM(total_tokens),0), COUNT(*) FROM token_usage").fetchone()
    rows = [dict(r) for r in rows]
    return templates.TemplateResponse(request, "usage.html", _ctx(request, rows=rows, tot=tot))


@app.get("/plan", response_class=HTMLResponse)
def plan_page(request: Request):
    db.init()
    return templates.TemplateResponse(request, "plan.html", _ctx(request))


@app.post("/plan", response_class=HTMLResponse)
def plan_submit(request: Request, salary: float = Form(None), context: str = Form(None), goal: str = Form(None)):
    db.init()
    txns = repo.list_transactions(limit=200)
    lines = [f"{t['date']} | {t['description']} | {t['category_name'] or '-'} | {t['amount_cents']/100.0:.2f}" for t in txns]
    ctx = "Transactions:\n" + "\n".join(lines)
    from datetime import date as _d
    today = _d.today()
    months = []
    for i in range(3):
        m = today.month - i; y = today.year
        while m <= 0:
            m += 12; y -= 1
        months.append(f"{y:04d}-{m:02d}")
    mt_lines = []
    for mm in months:
        mt = repo.monthly_totals(mm)
        mt_lines.append(f"{mm}: income R$ {mt['income_cents']/100.0:.2f}, expenses R$ {abs(mt['expense_cents'])/100.0:.2f}")
    ctx += "\n\nMonthly totals:\n" + "\n".join(mt_lines)
    mem = repo.memories_as_context()
    graph = repo.graph_as_context()
    extra = "\n\n".join(x for x in (mem, graph) if x)
    if extra:
        ctx += "\n\n" + extra
    if salary is not None:
        ctx += f"\n\nMonthly salary/income: R$ {salary:.2f}"
    if context:
        ctx += f"\n\nUser context: {context}"
    ctx += f"\n\nUser goal: {goal or 'improve financial health'}"
    from ..i18n import get_language, language_name
    system = ("You are a personal financial planner. Analyze the data and user context and produce a practical monthly plan. "
              "Respond in " + language_name(get_language()) + ".")
    try:
        answer = ai.chat(system, ctx)
    except Exception as e:
        answer = f"Error: {e}"
    return templates.TemplateResponse(request, "_answer.html", {"request": request, "answer": answer})




@app.get("/plan/run", response_class=HTMLResponse)
def plan_run(request: Request, salary: str = "", context: str = "", goal: str = ""):
    db.init()
    txns = repo.list_transactions(limit=200)
    lines = [f"{t['date']} | {t['description']} | {t['category_name'] or '-'} | {t['amount_cents']/100.0:.2f}" for t in txns]
    ctx = "Transactions:\n" + "\n".join(lines)
    from datetime import date as _d
    today = _d.today()
    months = []
    for i in range(3):
        m = today.month - i; y = today.year
        while m <= 0:
            m += 12; y -= 1
        months.append(f"{y:04d}-{m:02d}")
    mt_lines = []
    for mm in months:
        mt = repo.monthly_totals(mm)
        mt_lines.append(f"{mm}: income R$ {mt['income_cents']/100.0:.2f}, expenses R$ {abs(mt['expense_cents'])/100.0:.2f}")
    ctx += "\n\nMonthly totals:\n" + "\n".join(mt_lines)
    mem = repo.memories_as_context()
    graph = repo.graph_as_context()
    extra = "\n\n".join(x for x in (mem, graph) if x)
    if extra:
        ctx += "\n\n" + extra
    if salary:
        try:
            ctx += f"\n\nMonthly salary/income: R$ {float(salary):.2f}"
        except Exception:
            pass
    if context:
        ctx += f"\n\nUser context: {context}"
    ctx += f"\n\nUser goal: {goal or 'improve financial health'}"
    from ..i18n import get_language, language_name
    system = ("You are a personal financial planner. Analyze the data and user context and produce a practical monthly plan. "
              "Respond in " + language_name(get_language()) + ".")
    try:
        answer = ai.chat(system, ctx)
    except Exception as e:
        answer = f"Error: {e}"
    return templates.TemplateResponse(request, "_answer.html", {"request": request, "answer": answer})


@app.get("/review", response_class=HTMLResponse)
def review_page(request: Request, month: str = None):
    db.init()
    if not month:
        month = date.today().strftime("%Y-%m")
    return templates.TemplateResponse(request, "review.html", _ctx(request, month=month))


@app.get("/review/run", response_class=HTMLResponse)
def review_run(request: Request, month: str = None):
    db.init()
    if not month:
        month = date.today().strftime("%Y-%m")
    mt = repo.monthly_totals(month)
    y, m = month.split("-")
    import calendar
    last = calendar.monthrange(int(y), int(m))[1]
    start = f"{month}-01"; end = f"{month}-{last:02d}"
    cat_rows = repo.summary_by_category(start=start, end=end)
    cat_lines = [f"{r['category'] or '(uncategorized)'}: R$ {r['total_cents']/100.0:.2f}" for r in cat_rows]
    txns = repo.list_transactions(start=start, end=end, limit=50)
    exp = sorted([t for t in txns if t["amount_cents"] < 0], key=lambda t: t["amount_cents"])[:10]
    exp_lines = [f"{t['date']} {t['description']}: R$ {t['amount_cents']/100.0:.2f}" for t in exp]
    context = (f"Month: {month}\nIncome: R$ {mt['income_cents']/100.0:.2f}\nExpenses: R$ {abs(mt['expense_cents'])/100.0:.2f}\n"
               f"Balance: R$ {(mt['income_cents']+mt['expense_cents'])/100.0:.2f}\nTransactions: {mt['count']}\n\n"
               "By category:\n" + "\n".join(cat_lines) + "\n\nLargest expenses:\n" + "\n".join(exp_lines))
    from ..i18n import get_language, language_name
    system = ("You are a personal financial analyst. Review the month: highlights, where most was spent, alerts, and 3 improvement suggestions. Concise. "
              "Respond in " + language_name(get_language()) + ".")
    try:
        answer = ai.chat(system, context)
    except Exception as e:
        answer = f"Error: {e}"
    return templates.TemplateResponse(request, "_answer.html", {"request": request, "answer": answer})


@app.get("/export")
def export_csv(account: str = None, start: str = None, end: str = None):
    db.init()
    rows = repo.list_transactions(account=account, start=start, end=end, limit=100000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "date", "account", "description", "category", "amount", "notes"])
    for r in rows:
        w.writerow([r["id"], r["date"], r["account_name"], r["description"], r["category_name"] or "", r["amount_cents"]/100.0, r.get("notes") or ""])
    from fastapi.responses import Response
    return Response(content=buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=summa_export.csv"})


@app.get("/chart", response_class=HTMLResponse)
def chart_page(request: Request, month: str = None):
    db.init()
    if not month:
        month = date.today().strftime("%Y-%m")
    y, m = month.split("-")
    import calendar
    last = calendar.monthrange(int(y), int(m))[1]
    start = f"{month}-01"; end = f"{month}-{last:02d}"
    rows = repo.summary_by_category(start=start, end=end)
    data = [{"category": r["category"] or "(uncategorized)", "total": abs(r["total_cents"])/100.0} for r in rows if (r["total_cents"] or 0) < 0]
    data.sort(key=lambda x: x["total"], reverse=True)
    maxv = max((d["total"] for d in data), default=1)
    return templates.TemplateResponse(request, "chart.html", _ctx(request, month=month, data=data, maxv=maxv))




@app.get("/set-lang")
def set_lang(lang: str, request: Request):
    db.init()
    try:
        from .. import repo
        repo.add_memory("__web_lang", lang, scope="web")
    except Exception:
        pass
    # also persist in settings
    try:
        with db.db() as conn:
            conn.execute("INSERT INTO settings(key,value) VALUES('language',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (lang,))
    except Exception:
        pass
    import os
    os.environ["SUMMA_LANGUAGE"] = lang
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)



@app.get("/health")
def health():
    db.init()
    try:
        with db.db() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "version": "0.1.0"}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=503)



@app.get("/search", response_class=HTMLResponse)
def search_page(request: Request, q: str = ""):
    db.init()
    rows = []
    if q:
        all_txns = repo.list_transactions(limit=100000)
        ql = q.lower()
        rows = [t for t in all_txns if ql in (t.get("description") or "").lower()
                or ql in (t.get("category_name") or "").lower()
                or ql in (t.get("account_name") or "").lower()]
    return templates.TemplateResponse(request, "search.html", _ctx(request, q=q, rows=rows, from_cents=models.from_cents))



@app.post("/graph/add")
def graph_add(subject: str = Form(...), predicate: str = Form(...), object: str = Form(...)):
    db.init()
    repo.add_triple(subject, predicate, object)
    return RedirectResponse("/graph", status_code=303)


@app.post("/graph/remove")
def graph_remove(subject: str = Form(...), predicate: str = Form(...), object: str = Form(...)):
    db.init()
    repo.delete_triple(subject, predicate, object)
    return RedirectResponse("/graph", status_code=303)


def run_web(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)
