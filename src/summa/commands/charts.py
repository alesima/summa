"""Chart commands."""
from __future__ import annotations

from typing import Optional

import calendar
import typer

from .. import db, repo, charts
from ..console import console


def register(app: typer.Typer) -> None:
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
