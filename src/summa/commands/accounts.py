"""Account-related commands."""
from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from .. import db, repo, models
from ..console import console


def register(app: typer.Typer) -> None:
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
            console.print(f"[red]Error:[/red] {e}")
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
