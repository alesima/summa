"""CLI for summa."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from . import db, repo, models, importers, ai
from .i18n import get_language, set_language, SUPPORTED, language_name
from . import charts
from . import tui
from .models import to_cents, from_cents

app = typer.Typer(name="summa", help="Terminal personal finance tracker with AI.", no_args_is_help=True)
console = Console()

# ---------- init ----------
@app.command()
def init():
    """Initialize the database."""
    db.init()
    console.print("[green]Database initialized at[/green]", db.db_path())
    accs = repo.list_accounts()
    if not accs:
        console.print("Tip: create an account with [bold]summa account add <name>[/bold].")


# ---------- account ----------
account_app = typer.Typer(help="Manage accounts.")
app.add_typer(account_app, name="account")


@account_app.command("add")
def account_add(
    name: str,
    type: str = typer.Option("checking", "--type", "-t", help="checking|savings|credit|cash|investment"),
    currency: str = typer.Option("BRL", "--currency", "-c"),
):
    """Add an account."""
    db.init()
    try:
        aid = repo.add_account(models.Account(name=name, type=type, currency=currency))
    except Exception as e:
        console.print(f"[red]Erro:[/red] {e}")
        raise typer.Exit(1)
    console.print(f"[green]Account created:[/green] {name} (id {aid})")


@account_app.command("list")
def account_list():
    """List accounts."""
    db.init()
    rows = repo.list_accounts()
    t = Table("ID", "Name", "Type", "Currency")
    for r in rows:
        t.add_row(str(r["id"]), r["name"], r["type"], r["currency"])
    console.print(t if rows else "No accounts.")


@account_app.command("remove")
def account_remove(name: str):
    """Remove an account (and its transactions)."""
    db.init()
    if repo.delete_account(name):
        console.print(f"[green]Removed:[/green] {name}")
    else:
        console.print(f"[red]Not found:[/red] {name}")
        raise typer.Exit(1)


# ---------- category ----------
category_app = typer.Typer(help="Manage categories.")
app.add_typer(category_app, name="category")


@category_app.command("list")
def category_list(kind: Optional[str] = typer.Option(None, "--kind", "-k")):
    """List categories."""
    db.init()
    rows = repo.list_categories(kind)
    t = Table("ID", "Name", "Type")
    for r in rows:
        t.add_row(str(r["id"]), r["name"], r["kind"])
    console.print(t)


@category_app.command("add")
def category_add(name: str, kind: str = typer.Option("expense", "--kind", "-k")):
    """Add a category."""
    db.init()
    cid = repo.add_category(models.Category(name=name, kind=kind))
    console.print(f"[green]Category created:[/green] {name} (id {cid})")


# ---------- transactions ----------
tx_app = typer.Typer(help="Manage transactions.")
app.add_typer(tx_app, name="tx")


@tx_app.command("add")
def tx_add(
    amount: float = typer.Argument(..., help="Amount (positive). Use --income for income."),
    description: str = typer.Argument(..., help="Description."),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account name/ID."),
    date_str: Optional[str] = typer.Option(None, "--date", "-d", help="YYYY-MM-DD (default: today)."),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    income: bool = typer.Option(False, "--income", "-i", help="Mark as income (positive amount)."),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    """Add a transaction."""
    db.init()
    accounts = repo.list_accounts()
    if not accounts:
        console.print("[red]Create an account first: summa account add <name>[/red]")
        raise typer.Exit(1)
    acc = repo.get_account(account) if account else accounts[0]
    if not acc:
        console.print(f"[red]Account not found:[/red] {account}")
        raise typer.Exit(1)
    d = date_str or date.today().isoformat()
    # validate date
    try:
        datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        console.print("[red]Invalid date. Use YYYY-MM-DD.[/red]")
        raise typer.Exit(1)
    cents = to_cents(amount)
    if not income:
        cents = -abs(cents)
    else:
        cents = abs(cents)
    cat_id = None
    if category:
        cat = repo.get_category(category)
        if not cat:
            console.print(f"[red]Category not found:[/red] {category}")
            raise typer.Exit(1)
        cat_id = cat["id"]
    tx = models.Transaction(
        account_id=acc["id"], date=date.fromisoformat(d), amount_cents=cents,
        description=description, category_id=cat_id, notes=notes,
    )
    tid = repo.add_transaction(tx)
    console.print(f"[green]Transaction #{tid}[/green] {d}  {description}  R$ {from_cents(cents)}")


@tx_app.command("list")
def tx_list(
    account: Optional[str] = typer.Option(None, "--account", "-a"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    start: Optional[str] = typer.Option(None, "--start", "-s"),
    end: Optional[str] = typer.Option(None, "--end", "-e"),
    uncategorized: bool = typer.Option(False, "--uncategorized", "-u"),
    limit: int = typer.Option(50, "--limit", "-n"),
):
    """List transactions."""
    db.init()
    rows = repo.list_transactions(account=account, category=category, start=start, end=end,
                                  uncategorized=uncategorized, limit=limit)
    t = Table("ID", "Date", "Account", "Description", "Category", "Amount")
    for r in rows:
        val = from_cents(r["amount_cents"])
        color = "green" if r["amount_cents"] > 0 else "red"
        t.add_row(str(r["id"]), r["date"], r["account_name"], r["description"],
                  r["category_name"] or "-", f"[{color}]{val}[/{color}]")
    console.print(t if rows else "No transactions.")


@tx_app.command("delete")
def tx_delete(tx_id: int):
    """Remove a transaction."""
    db.init()
    if repo.delete_transaction(tx_id):
        console.print(f"[green]Removed #{tx_id}[/green]")
    else:
        console.print(f"[red]Not found #{tx_id}[/red]")
        raise typer.Exit(1)


@tx_app.command("import")
def tx_import(
    file: Path = typer.Argument(..., exists=True, readable=True),
    account: Optional[str] = typer.Option(None, "--account", "-a"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show only, do not save."),
    categorize: bool = typer.Option(False, "--categorize", "-C", help="Auto-categorize with AI after import."),
):
    """Import a bank statement (CSV/OFX)."""
    db.init()
    accounts = repo.list_accounts()
    if not accounts:
        console.print("[red]Create an account first.[/red]")
        raise typer.Exit(1)
    acc = repo.get_account(account) if account else (accounts[0] if len(accounts) == 1 else None)
    if not acc:
        console.print("[red]Specify --account (there is more than one account).[/red]")
        raise typer.Exit(1)
    parsed = importers.parse_statement(file)
    if not parsed:
        console.print("[red]No transactions found in file.[/red]")
        raise typer.Exit(1)
    console.print(f"[cyan]{len(parsed)} transactions found.[/cyan]")
    t = Table("Date", "Description", "Amount")
    for p in parsed[:20]:
        t.add_row(p["date"], p["description"][:40], from_cents(to_cents(p["amount"])))
    if len(parsed) > 20:
        console.print(f"... and {len(parsed)-20} more")
    console.print(t)
    if dry_run:
        return
    # detect transfer category
    transfer_cat = repo.get_category("Transferência")
    transfer_cat_id = transfer_cat["id"] if transfer_cat else None
    # credit card account names for matching
    all_accounts = repo.list_accounts()
    card_names = [a["name"].lower() for a in all_accounts if a["type"] == "credit" and a["id"] != acc["id"]]
    payment_keywords = ("pagamento", "payment", "fatura", "cartao", "cartão", "card")

    def is_transfer(p):
        desc_l = (p["description"] or "").lower()
        amt = p["amount"]
        # importing into a credit account: positive amounts are payments received
        if acc["type"] == "credit" and amt > 0:
            return True
        # importing into a bank/cash account: description matches a card payment
        if acc["type"] != "credit":
            if any(kw in desc_l for kw in payment_keywords):
                return True
            if any(cn in desc_l for cn in card_names):
                return True
        return False

    n = 0
    skipped = 0
    for p in parsed:
        amt_cents = to_cents(p["amount"])
        # dedup: skip if identical transaction already exists
        existing = repo.list_transactions(account=acc["name"], start=p["date"], end=p["date"], limit=1000)
        dup = any(e["amount_cents"] == amt_cents and e["description"] == p["description"] for e in existing)
        if dup:
            skipped += 1
            continue
        cat_id = transfer_cat_id if (transfer_cat_id and is_transfer(p)) else None
        tx = models.Transaction(
            account_id=acc["id"], date=date.fromisoformat(p["date"]),
            amount_cents=amt_cents, description=p["description"], raw=p["raw"],
            category_id=cat_id,
        )
        repo.add_transaction(tx)
        n += 1
    console.print(f"[green]Imported {n} transactions into account {acc['name']}.[/green]")
    if skipped:
        console.print(f"[yellow]Skipped {skipped} duplicate transactions.[/yellow]")
    if categorize:
        # run categorize apply
        txns = repo.list_transactions(uncategorized=True, limit=500)
        if txns:
            cats = list(dict.fromkeys([c["name"] for c in repo.list_categories()]))
            try:
                suggestions = ai.categorize_transactions(txns, cats)
                cat_by_name = {c["name"]: c["id"] for c in repo.list_categories()}
                applied = 0
                for sug in suggestions:
                    cid = cat_by_name.get(sug.get("category"))
                    if cid is not None:
                        repo.update_transaction_category(sug["id"], cid)
                        applied += 1
                console.print(f"[green]AI categorized {applied}/{len(txns)} transactions.[/green]")
            except Exception as e:
                console.print(f"[yellow]AI categorization failed:[/yellow] {e}")
    else:
        console.print("Tip: run [bold]summa tx categorize --apply[/bold] to categorize with AI.")


@tx_app.command("categorize")
def tx_categorize(
    limit: int = typer.Option(50, "--limit", "-n"),
    apply: bool = typer.Option(False, "--apply", help="Apply suggestions automatically."),
):
    """Suggest categories with AI for uncategorized transactions."""
    db.init()
    txns = repo.list_transactions(uncategorized=True, limit=limit)
    if not txns:
        console.print("No uncategorized transactions.")
        return
    cats = [c["name"] for c in repo.list_categories(kind="expense")] + \
           [c["name"] for c in repo.list_categories(kind="income")]
    # unique
    cats = list(dict.fromkeys(cats))
    try:
        suggestions = ai.categorize_transactions(txns, cats)
    except Exception as e:
        console.print(f"[red]AI error:[/red] {e}")
        raise typer.Exit(1)
    cat_by_name = {c["name"]: c["id"] for c in repo.list_categories()}
    t = Table("ID", "Description", "Suggestion")
    for s in suggestions:
        t.add_row(str(s.get("id")), next((x["description"] for x in txns if x["id"] == s.get("id")), ""),
                  s.get("category", "-"))
    console.print(t)
    if apply:
        applied = 0
        for s in suggestions:
            cid = cat_by_name.get(s.get("category"))
            if cid is not None:
                repo.update_transaction_category(s["id"], cid)
                applied += 1
        console.print(f"[green]Applied {applied} categories.[/green]")
    else:
        console.print("Use [bold]--apply[/bold] to apply.")


# ---------- budget ----------
budget_app = typer.Typer(help="Budgets.")
app.add_typer(budget_app, name="budget")


@budget_app.command("set")
def budget_set(category: str, month: str, amount: float):
    """Set a budget for a category in a month (YYYY-MM)."""
    db.init()
    cat = repo.get_category(category)
    if not cat:
        console.print(f"[red]Category not found:[/red] {category}")
        raise typer.Exit(1)
    repo.set_budget(cat["id"], month, to_cents(amount))
    console.print(f"[green]Budget {category} {month}: R$ {amount:.2f}[/green]")


@budget_app.command("show")
def budget_show(month: str):
    """Show budget status for a month (YYYY-MM)."""
    db.init()
    rows = repo.budget_status(month)
    t = Table("Category", "Budget", "Spent", "Remaining", "%")
    for r in rows:
        budget = r["budget_cents"]
        spent = r["spent_cents"]
        remaining = budget - spent
        pct = (spent / budget * 100) if budget else 0
        color = "red" if (budget and spent > budget) else "green"
        t.add_row(r["category"], from_cents(budget), from_cents(spent),
                  f"[{color}]{from_cents(remaining)}[/{color}]", f"{pct:.0f}%")
    console.print(t)


# ---------- report ----------
report_app = typer.Typer(help="Reports.")
app.add_typer(report_app, name="report")


@report_app.command("summary")
def report_summary(start: Optional[str] = None, end: Optional[str] = None):
    """Summary by category."""
    db.init()
    rows = repo.summary_by_category(start=start, end=end)
    t = Table("Category", "Total", "Count")
    total = 0
    for r in rows:
        t.add_row(r["category"] or "(uncategorized)", from_cents(r["total_cents"]), str(r["n"]))
        total += r["total_cents"]
    console.print(t)
    console.print(f"[bold]Total: R$ {from_cents(total)}[/bold]")


@report_app.command("monthly")
def report_monthly(month: str):
    """Monthly summary (YYYY-MM)."""
    db.init()
    mt = repo.monthly_totals(month)
    console.print(Panel(
        f"Month: {month}\n"
        f"Income: R$ {from_cents(mt['income_cents'])}\n"
        f"Expenses: R$ {from_cents(abs(mt['expense_cents']))}\n"
        f"Balance: R$ {from_cents(mt['income_cents'] + mt['expense_cents'])}\n"
        f"Transactions: {mt['count']}",
        title="Monthly summary",
    ))
    # top categories
    y, m = month.split("-")
    last = calendar.monthrange(int(y), int(m))[1]
    start = f"{month}-01"; end = f"{month}-{last:02d}"
    rows = repo.summary_by_category(start=start, end=end)
    # expenses only
    exp = [r for r in rows if (r["total_cents"] or 0) < 0]
    exp.sort(key=lambda r: r["total_cents"])
    t = Table("Category", "Spent")
    for r in exp[:10]:
        t.add_row(r["category"] or "(uncategorized)", from_cents(abs(r["total_cents"])))
    console.print(t)


# ---------- ask / chat ----------
@app.command()
def ask(question: str):
    """Ask a natural language question about your finances (uses AI)."""
    db.init()
    # Build context: recent transactions + monthly summary + categories
    txns = repo.list_transactions(limit=200)
    lines = []
    for t in txns:
        lines.append(f"{t['date']} | {t['account_name']} | {t['description']} | {t['category_name'] or '-'} | {from_cents(t['amount_cents'])}")
    context = "Transactions (date|account|description|category|amount):\n" + "\n".join(lines)
    # monthly totals last 6 months
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
        mt_lines.append(f"{mm}: income R$ {from_cents(mt['income_cents'])}, expenses R$ {from_cents(abs(mt['expense_cents']))}, balance R$ {from_cents(mt['income_cents']+mt['expense_cents'])}")
    context += "\n\nMonthly totals:\n" + "\n".join(mt_lines)
    try:
        ans = ai.answer_question(question, context)
    except Exception as e:
        console.print(f"[red]AI error:[/red] {e}")
        raise typer.Exit(1)
    console.print(Panel(ans, title="Answer"))


@app.command()
def chat():
    """Interactive chat (REPL)."""
    db.init()
    console.print("Chat mode. Type 'exit' to quit.")
    while True:
        try:
            q = typer.prompt(">")
        except (EOFError, KeyboardInterrupt):
            break
        if q.strip().lower() in ("exit", "quit", "sair"):
            break
        # reuse ask logic by calling
        ctx_txns = repo.list_transactions(limit=200)
        lines = [f"{t['date']} | {t['description']} | {t['category_name'] or '-'} | {from_cents(t['amount_cents'])}" for t in ctx_txns]
        context = "Transactions:\n" + "\n".join(lines)
        try:
            ans = ai.answer_question(q, context)
            console.print(ans)
        except Exception as e:
            console.print(f"[red]Erro:[/red] {e}")




@app.command("lang")
def lang_cmd(code: Optional[str] = typer.Argument(None, help="Language code, e.g. en, pt-BR, es.")):
    """View or set the conversation language."""
    db.init()
    if code is None:
        cur = get_language()
        console.print(f"Current language: {cur} ({language_name(cur)})")
        console.print("Supported: " + ", ".join(f"{k} ({v})" for k, v in SUPPORTED.items()))
        return
    try:
        set_language(code)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Language set to {code} ({language_name(code)}).[/green]")




# ---------- chart ----------
chart_app = typer.Typer(help="Terminal charts.")
app.add_typer(chart_app, name="chart")


@chart_app.command("spending")
def chart_spending(month: Optional[str] = typer.Option(None, "--month", "-m")):
    """Bar chart of spending by category for a month."""
    db.init()
    if not month:
        from datetime import date as _d
        month = _d.today().strftime("%Y-%m")
    y, m = month.split("-")
    import calendar
    last = calendar.monthrange(int(y), int(m))[1]
    start = f"{month}-01"; end = f"{month}-{last:02d}"
    rows = repo.summary_by_category(start=start, end=end)
    data = [{"category": r["category"] or "(uncategorized)",
             "total": abs(r["total_cents"]) / 100.0} for r in rows if (r["total_cents"] or 0) < 0]
    charts.spending_by_category(data, title=f"Spending by category - {month}")


@chart_app.command("trend")
def chart_trend(months: int = typer.Option(6, "--months", "-n")):
    """Monthly income vs expense trend."""
    db.init()
    from datetime import date as _d
    today = _d.today()
    rows = []
    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12; y -= 1
        mm = f"{y:04d}-{m:02d}"
        mt = repo.monthly_totals(mm)
        rows.append({"month": mm,
                     "income": mt["income_cents"] / 100.0,
                     "expense": abs(mt["expense_cents"]) / 100.0})
    charts.monthly_trend(rows, title=f"Monthly trend ({months} months)")


# ---------- export ----------
@app.command("export")
def export_cmd(
    path: Path = typer.Argument(..., help="Output CSV file path."),
    account: Optional[str] = typer.Option(None, "--account", "-a"),
    start: Optional[str] = typer.Option(None, "--start", "-s"),
    end: Optional[str] = typer.Option(None, "--end", "-e"),
):
    """Export transactions to a CSV file."""
    db.init()
    rows = repo.list_transactions(account=account, start=start, end=end, limit=100000)
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "date", "account", "description", "category", "amount", "notes"])
        for r in rows:
            w.writerow([r["id"], r["date"], r["account_name"], r["description"],
                        r["category_name"] or "", r["amount_cents"] / 100.0, r.get("notes") or ""])
    console.print(f"[green]Exported {len(rows)} transactions to {path}[/green]")


# ---------- fx ----------
fx_app = typer.Typer(help="Exchange rates.")
app.add_typer(fx_app, name="fx")


@fx_app.command("set")
def fx_set(base: str, quote: str, rate: float):
    """Set an exchange rate (base -> quote)."""
    db.init()
    with db.db() as conn:
        conn.execute(
            """INSERT INTO fx_rates(base_currency, quote_currency, rate) VALUES (?,?,?)
               ON CONFLICT(base_currency, quote_currency) DO UPDATE SET rate=excluded.rate, updated_at=datetime('now')""",
            (base.upper(), quote.upper(), rate),
        )
    console.print(f"[green]{base.upper()} -> {quote.upper()} = {rate}[/green]")


@fx_app.command("list")
def fx_list():
    """List exchange rates."""
    db.init()
    with db.db() as conn:
        rows = conn.execute("SELECT * FROM fx_rates ORDER BY base_currency, quote_currency").fetchall()
    t = Table("Base", "Quote", "Rate", "Updated")
    for r in rows:
        t.add_row(r["base_currency"], r["quote_currency"], str(r["rate"]), r["updated_at"])
    console.print(t if rows else "No rates.")




@app.command("dashboard")
def dashboard_cmd():
    """Launch the interactive TUI dashboard."""
    db.init()
    tui.run_dashboard()




@app.command("import")
def import_cmd(
    file: Path = typer.Argument(..., exists=True, readable=True),
    account: Optional[str] = typer.Option(None, "--account", "-a"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show only, do not save."),
    categorize: bool = typer.Option(False, "--categorize", "-C", help="Auto-categorize with AI after import."),
):
    """Import a bank statement (CSV/OFX)."""
    tx_import(file, account=account, dry_run=dry_run, categorize=categorize)



def main():
    app()


if __name__ == "__main__":
    main()


# ---------- plan / review ----------
@app.command()
def plan(
    goal: Optional[str] = typer.Option(None, "--goal", "-g", help="Goal, e.g. 'save 20% of income'."),
    months: int = typer.Option(3, "--months", "-m", help="Months of history to analyze."),
):
    """Generate a financial plan with AI (analysis + budget suggestions)."""
    db.init()
    from datetime import date as _d
    today = _d.today()
    month_list = []
    for i in range(months):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12; y -= 1
        month_list.append(f"{y:04d}-{m:02d}")
    mt_lines = []
    for mm in month_list:
        mt = repo.monthly_totals(mm)
        mt_lines.append(f"{mm}: income R$ {from_cents(mt['income_cents'])}, expenses R$ {from_cents(abs(mt['expense_cents']))}, balance R$ {from_cents(mt['income_cents']+mt['expense_cents'])}, n={mt['count']}")
    # category totals for latest month
    latest = month_list[0]
    y, m = latest.split("-")
    import calendar
    last = calendar.monthrange(int(y), int(m))[1]
    start = f"{latest}-01"; end = f"{latest}-{last:02d}"
    cat_rows = repo.summary_by_category(start=start, end=end)
    cat_lines = [f"{r['category'] or '(sem categoria)'}: R$ {from_cents(abs(r['total_cents']))}" for r in cat_rows if (r['total_cents'] or 0) < 0]
    budgets = repo.list_budgets(latest)
    bud_lines = [f"{b['category_name']}: R$ {from_cents(b['amount_cents'])}" for b in budgets]
    context = (
        "Monthly history:\n" + "\n".join(mt_lines) +
        "\n\nSpending by category (current month):\n" + "\n".join(cat_lines) +
        "\n\nCurrent budgets:\n" + ("\n".join(bud_lines) if bud_lines else "(none)") +
        f"\n\nUser goal: {goal or 'improve financial health'}"
    )
    lang = language_name(get_language())
    system = (
        "You are a personal financial planner. Analyze the data and produce a practical, concise plan: "
        "1) Situation diagnosis; 2) 3-5 priority actions; 3) Suggested budget per category (values in R$); "
        "4) Monthly savings goal. Be realistic and specific. Do not invent data. "
        f"Respond in {lang}."
    )
    try:
        ans = ai.chat(system, context)
    except Exception as e:
        console.print(f"[red]AI error:[/red] {e}")
        raise typer.Exit(1)
    console.print(Panel(ans, title="Financial plan (AI)"))


@app.command()
def review(month: Optional[str] = typer.Option(None, "--month", "-m", help="YYYY-MM (default: current month).")):
    """Monthly review with AI insights."""
    db.init()
    if not month:
        from datetime import date as _d
        month = _d.today().strftime("%Y-%m")
    mt = repo.monthly_totals(month)
    y, m = month.split("-")
    import calendar
    last = calendar.monthrange(int(y), int(m))[1]
    start = f"{month}-01"; end = f"{month}-{last:02d}"
    cat_rows = repo.summary_by_category(start=start, end=end)
    cat_lines = [f"{r['category'] or '(sem categoria)'}: R$ {from_cents(r['total_cents'])} (n={r['n']})" for r in cat_rows]
    txns = repo.list_transactions(start=start, end=end, limit=50)
    # top expenses
    exp = sorted([t for t in txns if t["amount_cents"] < 0], key=lambda t: t["amount_cents"])[:10]
    exp_lines = [f"{t['date']} {t['description']}: R$ {from_cents(t['amount_cents'])}" for t in exp]
    context = (
        f"Month: {month}\n"
        f"Income: R$ {from_cents(mt['income_cents'])}\n"
        f"Expenses: R$ {from_cents(abs(mt['expense_cents']))}\n"
        f"Balance: R$ {from_cents(mt['income_cents']+mt['expense_cents'])}\n"
        f"Transactions: {mt['count']}\n\n"
        "By category:\n" + "\n".join(cat_lines) +
        "\n\nLargest expenses:\n" + "\n".join(exp_lines)
    )
    lang = language_name(get_language())
    system = (
        "You are a personal financial analyst. Review the month: "
        "highlights, where most was spent, alerts (above-normal spending), and 3 improvement suggestions. Concise. "
        f"Respond in {lang}."
    )
    try:
        ans = ai.chat(system, context)
    except Exception as e:
        console.print(f"[red]AI error:[/red] {e}")
        raise typer.Exit(1)
    console.print(Panel(ans, title=f"Review {month}"))
