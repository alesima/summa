"""CLI entry point for summa."""
from __future__ import annotations

import typer

from .console import console  # noqa: F401  (re-exported for backwards compat)
from .commands import (
    accounts,
    categories,
    transactions,
    budgets,
    reports,
    charts,
    fx,
    system,
    ai,
    memory,
)

app = typer.Typer(name="summa", help="Terminal personal finance tracker with AI.", no_args_is_help=True)


def _register_all() -> None:
    accounts.register(app)
    categories.register(app)
    transactions.register(app)
    budgets.register(app)
    reports.register(app)
    charts.register(app)
    fx.register(app)
    system.register(app)
    ai.register(app)
    memory.register(app)


_register_all()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
