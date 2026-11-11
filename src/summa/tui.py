"""Textual-based TUI dashboard."""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static

from . import db, repo
from .models import from_cents


class SummaDashboard(App):
    CSS = """
    Screen { layout: vertical; }
    #accounts, #transactions, #budget { border: solid green; }
    .box { padding: 1; }
    """

    BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="accounts", classes="box"):
                yield Static("Accounts", classes="title")
                yield DataTable(id="acc_table")
            with Vertical(id="transactions", classes="box"):
                yield Static("Recent transactions", classes="title")
                yield DataTable(id="tx_table")
        with Vertical(id="budget", classes="box"):
            yield Static("Budget status (current month)", classes="title")
            yield DataTable(id="bud_table")
        yield Footer()

    def on_mount(self) -> None:
        self._load()

    def action_refresh(self) -> None:
        self._load()

    def _load(self) -> None:
        # accounts
        acc_table = self.query_one("#acc_table", DataTable)
        acc_table.clear(columns=True)
        acc_table.add_columns("Name", "Type", "Currency")
        for a in repo.list_accounts():
            acc_table.add_row(a["name"], a["type"], a["currency"])

        # transactions
        tx_table = self.query_one("#tx_table", DataTable)
        tx_table.clear(columns=True)
        tx_table.add_columns("Date", "Description", "Category", "Amount")
        for t in repo.list_transactions(limit=15):
            tx_table.add_row(t["date"], t["description"][:24],
                            t["category_name"] or "-", from_cents(t["amount_cents"]))

        # budget
        from datetime import date as _d
        month = _d.today().strftime("%Y-%m")
        bud_table = self.query_one("#bud_table", DataTable)
        bud_table.clear(columns=True)
        bud_table.add_columns("Category", "Budget", "Spent", "Remaining")
        for r in repo.budget_status(month):
            bud_table.add_row(r["category"], from_cents(r["budget_cents"]),
                             from_cents(r["spent_cents"]),
                             from_cents(r["budget_cents"] - r["spent_cents"]))


def run_dashboard() -> None:
    db.init()
    SummaDashboard().run()
