"""AI-related commands."""
from __future__ import annotations

from typing import Optional

import typer
from rich.panel import Panel

from .. import db, repo, ai
from ..console import console
from ..i18n import get_language, language_name


def register(app: typer.Typer) -> None:
    @app.command()
    def ask(question: str):
        """Ask a natural language question about your finances (uses AI)."""
        db.init()
        txns = repo.list_transactions(limit=200)
        lines = []
        for t in txns:
            lines.append(f"{t['date']} | {t['account_name']} | {t['description']} | {t['category_name'] or '-'} | {t['amount_cents']/100.0:.2f}")
        context = "Transactions (date|account|description|category|amount):\n" + "\n".join(lines)
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
            mt_lines.append(f"{mm}: income R$ {mt['income_cents']/100.0:.2f}, expenses R$ {abs(mt['expense_cents'])/100.0:.2f}, balance R$ {(mt['income_cents']+mt['expense_cents'])/100.0:.2f}")
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
        console.print("Chat mode. Type 'exit' to quit. (conversation memory enabled)")
        from ..i18n import get_language, language_name
        lang = language_name(get_language())
        ctx_txns = repo.list_transactions(limit=200)
        lines = [f"{t['date']} | {t['description']} | {t['category_name'] or '-'} | {t['amount_cents']/100.0:.2f}" for t in ctx_txns]
        mem = repo.memories_as_context() if hasattr(repo, "memories_as_context") else ""
        graph = repo.graph_as_context() if hasattr(repo, "graph_as_context") else ""
        extra = "\n\n".join(x for x in (mem, graph) if x)
        system = (
            "You are a personal finance assistant. Answer concisely using the provided data and knowledge graph. "
            f"Respond in {lang}.\n\nTransactions:\n" + "\n".join(lines) +
            ("\n\n" + extra if extra else "")
        )
        history = []
        while True:
            try:
                q = typer.prompt(">")
            except (EOFError, KeyboardInterrupt):
                break
            if q.strip().lower() in ("exit", "quit", "sair"):
                break
            history.append({"role": "user", "content": q})
            try:
                ans = ai.chat_with_history(system, history)
                history.append({"role": "assistant", "content": ans})
                console.print(ans)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                history.pop()

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
            mt_lines.append(f"{mm}: income R$ {mt['income_cents']/100.0:.2f}, expenses R$ {abs(mt['expense_cents'])/100.0:.2f}, balance R$ {(mt['income_cents']+mt['expense_cents'])/100.0:.2f}, n={mt['count']}")
        latest = month_list[0]
        y, m = latest.split("-")
        import calendar
        last = calendar.monthrange(int(y), int(m))[1]
        start = f"{latest}-01"; end = f"{latest}-{last:02d}"
        cat_rows = repo.summary_by_category(start=start, end=end)
        cat_lines = [f"{r['category'] or '(uncategorized)'}: R$ {abs(r['total_cents'])/100.0:.2f}" for r in cat_rows if (r['total_cents'] or 0) < 0]
        budgets = repo.list_budgets(latest)
        bud_lines = [f"{b['category_name']}: R$ {b['amount_cents']/100.0:.2f}" for b in budgets]
        context = (
            "Monthly history:\n" + "\n".join(mt_lines) +
            "\n\nSpending by category (current month):\n" + "\n".join(cat_lines) +
            "\n\nCurrent budgets:\n" + ("\n".join(bud_lines) if bud_lines else "(none)") +
            f"\n\nUser goal: {goal or 'improve financial health'}" +
            ("\n\n" + repo.graph_as_context() if repo.graph_as_context() else "")
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
        cat_lines = [f"{r['category'] or '(uncategorized)'}: R$ {r['total_cents']/100.0:.2f} (n={r['n']})" for r in cat_rows]
        txns = repo.list_transactions(start=start, end=end, limit=50)
        exp = sorted([t for t in txns if t["amount_cents"] < 0], key=lambda t: t["amount_cents"])[:10]
        exp_lines = [f"{t['date']} {t['description']}: R$ {t['amount_cents']/100.0:.2f}" for t in exp]
        context = (
            f"Month: {month}\n"
            f"Income: R$ {mt['income_cents']/100.0:.2f}\n"
            f"Expenses: R$ {abs(mt['expense_cents'])/100.0:.2f}\n"
            f"Balance: R$ {(mt['income_cents']+mt['expense_cents'])/100.0:.2f}\n"
            f"Transactions: {mt['count']}\n\n"
            "By category:\n" + "\n".join(cat_lines) +
            "\n\nLargest expenses:\n" + "\n".join(exp_lines) +
            ("\n\n" + repo.graph_as_context() if repo.graph_as_context() else "")
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
