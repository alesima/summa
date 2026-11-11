"""Budget commands."""
from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from .. import db, repo
from ..console import console


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
