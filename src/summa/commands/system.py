"""System-level commands: init, lang, export, import, dashboard."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .. import db, repo, models
from ..console import console
from ..i18n import get_language, set_language, SUPPORTED, language_name


def register(app: typer.Typer) -> None:
    @app.command()
    def init():
        """Initialize the database."""
        db.init()
        console.print("[green]Database initialized at[/green]", db.db_path())
        if not repo.list_accounts():
            console.print("Tip: create an account with [bold]summa account add <name>[/bold].")

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

    @app.command("import")
    def import_cmd(
        file: Path = typer.Argument(..., exists=True, readable=True),
        account: Optional[str] = typer.Option(None, "--account", "-a"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Show only, do not save."),
        categorize: bool = typer.Option(False, "--categorize", "-C", help="Auto-categorize with AI after import."),
    ):
        """Import a bank statement (CSV/OFX)."""
        # delegate to transactions module
        from .transactions import tx_import
        tx_import(file, account=account, dry_run=dry_run, categorize=categorize)

    @app.command("dashboard")
    def dashboard_cmd():
        """Launch the interactive TUI dashboard."""
        db.init()
        from .. import tui
        tui.run_dashboard()
