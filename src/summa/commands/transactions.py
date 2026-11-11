"""Transaction-related commands."""
from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from .. import db, repo, models, importers, ai
from ..console import console


def register(app: typer.Typer) -> None:
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
        try:
            datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            console.print("[red]Invalid date. Use YYYY-MM-DD.[/red]")
            raise typer.Exit(1)
        from ..models import to_cents
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
        from ..models import from_cents as fc
        console.print(f"[green]Transaction #{tid}[/green] {d}  {description}  R$ {fc(cents)}")

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
            val = r["amount_cents"] / 100.0
            color = "green" if r["amount_cents"] > 0 else "red"
            t.add_row(str(r["id"]), r["date"], r["account_name"], r["description"],
                      r["category_name"] or "-", f"[{color}]{val:.2f}[/{color}]")
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
        force: bool = typer.Option(False, "--force", help="Re-import even if document was already imported."),
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
        from rich.status import Status
        with Status("[bold cyan]Reading statement...[/bold cyan]", console=console, spinner="dots"):
            parsed = importers.parse_statement(file)
        if not parsed:
            console.print("[red]No transactions found in file.[/red]")
            raise typer.Exit(1)
        console.print(f"[cyan]{len(parsed)} transactions found.[/cyan]")
        t = Table("Date", "Description", "Amount")
        for p in parsed[:20]:
            t.add_row(p["date"], p["description"][:40], f"{p['amount']:.2f}")
        if len(parsed) > 20:
            console.print(f"... and {len(parsed)-20} more")
        console.print(t)
        if dry_run:
            return
        from rich.status import Status
        with Status("[bold cyan]Importing...[/bold cyan]", console=console, spinner="dots"):
            from ..services.import_service import import_statement
            result = import_statement(file, account_name=acc["name"], categorize=categorize, force=force)
        if result.get("duplicate_document"):
            ex = result.get("existing", {})
            console.print(f"[yellow]This document was already imported on {ex.get('imported_at')} ({ex.get('transactions_count')} transactions). Skipping.[/yellow]")
            return
        console.print(f"[green]Imported {result['imported']} transactions into account {acc['name']}.[/green]")
        if result["skipped"]:
            console.print(f"[yellow]Skipped {result['skipped']} duplicate transactions.[/yellow]")
        if categorize and result.get("categorized"):
            console.print(f"[green]AI categorized {result['categorized']} transactions.[/green]")
        if not categorize:
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
        cats = list(dict.fromkeys([c["name"] for c in repo.list_categories()]))
        try:
            from rich.status import Status
            with Status("[bold cyan]Categorizing with AI...[/bold cyan]", console=console, spinner="dots"):
                from ..services.decision_service import categorize as decide
                suggestions = decide(txns, cats)
        except Exception as e:
            console.print(f"[red]AI error:[/red] {e}")
            raise typer.Exit(1)
        t = Table("ID", "Description", "Suggestion")
        for s in suggestions:
            t.add_row(str(s.get("id")), next((x["description"] for x in txns if x["id"] == s.get("id")), ""),
                      s.get("category", "-"))
        console.print(t)
        if apply:
            cat_by_name = {c["name"]: c["id"] for c in repo.list_categories()}
            applied = 0
            for s in suggestions:
                cid = cat_by_name.get(s.get("category"))
                if cid is not None:
                    repo.update_transaction_category(s["id"], cid)
                    applied += 1
            console.print(f"[green]Applied {applied} categories.[/green]")
        else:
            console.print("Use [bold]--apply[/bold] to apply.")
