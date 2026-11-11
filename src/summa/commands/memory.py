"""Memory commands (persistent notes for the AI)."""
from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from .. import db, repo
from ..console import console


def register(app: typer.Typer) -> None:
    mem_app = typer.Typer(help="Persistent memory/notes for the AI.")
    app.add_typer(mem_app, name="memory")

    @mem_app.command("add")
    def memory_add(key: str, value: str, scope: str = typer.Option("global", "--scope", "-s")):
        """Add or update a memory note."""
        db.init()
        repo.add_memory(key, value, scope)
        console.print(f"[green]Memory saved:[/green] {key}")

    @mem_app.command("list")
    def memory_list(scope: Optional[str] = typer.Option(None, "--scope", "-s")):
        """List memory notes."""
        db.init()
        rows = repo.list_memories(scope)
        t = Table("Key", "Value", "Scope", "Updated")
        for r in rows:
            t.add_row(r["key"], r["value"], r["scope"], r["updated_at"])
        console.print(t if rows else "No memories.")

    @mem_app.command("remove")
    def memory_remove(key: str):
        """Remove a memory note."""
        db.init()
        if repo.delete_memory(key):
            console.print(f"[green]Removed:[/green] {key}")
        else:
            console.print(f"[red]Not found:[/red] {key}")
            raise typer.Exit(1)
