"""Category-related commands."""
from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from .. import db, repo, models
from ..console import console


def register(app: typer.Typer) -> None:
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
