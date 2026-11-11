"""Report commands."""
from __future__ import annotations

from typing import Optional

import calendar
import typer
from rich.panel import Panel
from rich.table import Table

from .. import db, repo
from ..console import console


def register(app: typer.Typer) -> None:
    report_app = typer.Typer(help="Reports.")
    app.add_typer(report_app, name="report")

    @report_app.command("summary")
    def report_summary(start: Optional[str] = None, end: Optional[str] = None):
        """Summary by category."""
        db.init()
        rows = repo.summary_by_category(start=start, end=end)
        t = Table("Category", "Total", "Count")
        total = 0
        from ..models import from_cents
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
        from ..models import from_cents
        console.print(Panel(
            f"Month: {month}\n"
            f"Income: R$ {from_cents(mt['income_cents'])}\n"
            f"Expenses: R$ {from_cents(abs(mt['expense_cents']))}\n"
            f"Balance: R$ {from_cents(mt['income_cents'] + mt['expense_cents'])}\n"
            f"Transactions: {mt['count']}",
            title="Monthly summary",
        ))
        y, m = month.split("-")
        last = calendar.monthrange(int(y), int(m))[1]
        start = f"{month}-01"; end = f"{month}-{last:02d}"
        rows = repo.summary_by_category(start=start, end=end)
        exp = [r for r in rows if (r["total_cents"] or 0) < 0]
        exp.sort(key=lambda r: r["total_cents"])
        t = Table("Category", "Spent")
        for r in exp[:10]:
            t.add_row(r["category"] or "(uncategorized)", from_cents(abs(r["total_cents"])))
        console.print(t)
