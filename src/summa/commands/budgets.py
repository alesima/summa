"""Budget commands."""
from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from .. import db, repo, models
from ..console import console
import calendar
from datetime import date as _date, datetime


def register(app: typer.Typer) -> None:
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
        from ..models import to_cents
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
            from ..models import from_cents
            t.add_row(r["category"], from_cents(budget), from_cents(spent),
                      f"[{color}]{from_cents(remaining)}[/{color}]", f"{pct:.0f}%")
        console.print(t)

    @budget_app.command("plan")
    def budget_plan(
        salary: float = typer.Argument(..., help="Monthly salary/income amount."),
        month: Optional[str] = typer.Option(None, "--month", "-m", help="YYYY-MM (default: current month)."),
        savings_pct: float = typer.Option(20.0, "--savings", "-s", help="Savings percentage of salary."),
        apply: bool = typer.Option(False, "--apply", help="Apply as budgets for the month."),
        history_months: int = typer.Option(3, "--history", "-H", help="Months of history for proportions."),
    ):
        """Plan monthly budget from salary."""
        db.init()
        if not month:
            month = _date.today().strftime("%Y-%m")
        from ..models import to_cents, from_cents

        # historical spending proportions
        from collections import defaultdict
        hist = defaultdict(int)
        total_hist = 0
        today = _date.today()
        for i in range(history_months):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12; y -= 1
            mm = f"{y:04d}-{m:02d}"
            yy, mm2 = mm.split("-")
            last = calendar.monthrange(int(yy), int(mm2))[1]
            start = f"{mm}-01"; end = f"{mm}-{last:02d}"
            for r in repo.summary_by_category(start=start, end=end):
                if (r["total_cents"] or 0) < 0 and r["category"]:
                    hist[r["category"]] += abs(r["total_cents"])
                    total_hist += abs(r["total_cents"])

        salary_cents = to_cents(salary)
        savings_cents = int(salary_cents * (savings_pct / 100.0))
        remaining = salary_cents - savings_cents

        expense_cats = [c for c in repo.list_categories(kind="expense")]

        # allocate
        alloc = {}
        if total_hist > 0:
            for c in expense_cats:
                prop = hist.get(c["name"], 0) / total_hist
                alloc[c["name"]] = int(remaining * prop)
        else:
            # equal split
            per = remaining // len(expense_cats) if expense_cats else 0
            for c in expense_cats:
                alloc[c["name"]] = per
        # adjust rounding to remaining
        diff = remaining - sum(alloc.values())
        if expense_cats and diff != 0:
            alloc[expense_cats[0]["name"]] += diff

        t = Table("Category", "Amount", "% of salary")
        for c in expense_cats:
            amt = alloc[c["name"]]
            pct = (amt / salary_cents * 100) if salary_cents else 0
            t.add_row(c["name"], from_cents(amt), f"{pct:.1f}%")
        console.print(t)
        console.print(f"[bold]Salary: R$ {salary:.2f}[/bold]")
        console.print(f"Savings ({savings_pct:.0f}%): R$ {savings_cents/100.0:.2f}")
        console.print(f"Allocated to expenses: R$ {remaining/100.0:.2f}")
        console.print(f"Total: R$ {(savings_cents+remaining)/100.0:.2f}")

        if apply:
            for c in expense_cats:
                repo.set_budget(c["id"], month, alloc[c["name"]])
            console.print(f"[green]Budgets applied for {month}.[/green]")
