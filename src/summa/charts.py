"""Terminal charts using rich."""
from __future__ import annotations

from typing import Iterable

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def _bar(value: float, max_value: float, width: int = 40) -> str:
    if max_value <= 0:
        return ""
    n = int(round((value / max_value) * width))
    n = max(0, min(width, n))
    return "█" * n


def spending_by_category(rows: list[dict], title: str = "Spending by category") -> None:
    # rows: list of {category, total} where total is positive spending amount
    if not rows:
        console.print("No data.")
        return
    data = sorted(rows, key=lambda r: r["total"], reverse=True)
    maxv = max(r["total"] for r in data) or 1
    lines = []
    for r in data:
        bar = _bar(r["total"], maxv)
        lines.append(f"{r['category'][:20]:<20} {bar} {r['total']:.2f}")
    console.print(Panel("\n".join(lines), title=title))


def monthly_trend(rows: list[dict], title: str = "Monthly trend") -> None:
    # rows: list of {month, income, expense}
    if not rows:
        console.print("No data.")
        return
    maxv = max(max(r["income"], r["expense"]) for r in rows) or 1
    lines = []
    for r in rows:
        inc_bar = _bar(r["income"], maxv, width=20)
        exp_bar = _bar(r["expense"], maxv, width=20)
        lines.append(f"{r['month']}  inc [{inc_bar:<20}] {r['income']:>10.2f}  exp [{exp_bar:<20}] {r['expense']:>10.2f}")
    console.print(Panel("\n".join(lines), title=title))
