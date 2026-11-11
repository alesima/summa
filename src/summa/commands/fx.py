"""Exchange rate commands."""
from __future__ import annotations

import typer
from rich.table import Table

from .. import db
from ..console import console


def register(app: typer.Typer) -> None:
    fx_app = typer.Typer(help="Exchange rates.")
    app.add_typer(fx_app, name="fx")

    @fx_app.command("set")
    def fx_set(base: str, quote: str, rate: float):
        """Set an exchange rate (base -> quote)."""
        db.init()
        with db.db() as conn:
            conn.execute(
                """INSERT INTO fx_rates(base_currency, quote_currency, rate) VALUES (?,?,?)
                   ON CONFLICT(base_currency, quote_currency) DO UPDATE SET rate=excluded.rate, updated_at=datetime('now')""",
                (base.upper(), quote.upper(), rate),
            )
        console.print(f"[green]{base.upper()} -> {quote.upper()} = {rate}[/green]")

    @fx_app.command("list")
    def fx_list():
        """List exchange rates."""
        db.init()
        with db.db() as conn:
            rows = conn.execute("SELECT * FROM fx_rates ORDER BY base_currency, quote_currency").fetchall()
        t = Table("Base", "Quote", "Rate", "Updated")
        for r in rows:
            t.add_row(r["base_currency"], r["quote_currency"], str(r["rate"]), r["updated_at"])
        console.print(t if rows else "No rates.")
