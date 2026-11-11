"""Knowledge graph commands (triples)."""
from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from .. import db, repo
from ..console import console


def register(app: typer.Typer) -> None:
    graph_app = typer.Typer(help="Knowledge graph (subject-predicate-object triples).")
    app.add_typer(graph_app, name="graph")

    @graph_app.command("add")
    def graph_add(subject: str, predicate: str, obj: str, confidence: float = typer.Option(1.0, "--confidence", "-c")):
        """Add a triple: subject predicate object."""
        db.init()
        repo.add_triple(subject, predicate, obj, confidence)
        console.print(f"[green]Triple added:[/green] {subject} --{predicate}--> {obj}")

    @graph_app.command("list")
    def graph_list(subject: Optional[str] = typer.Option(None, "--subject", "-s"),
                   predicate: Optional[str] = typer.Option(None, "--predicate", "-p"),
                   obj: Optional[str] = typer.Option(None, "--object", "-o")):
        """List triples (optionally filtered)."""
        db.init()
        rows = repo.list_triples(subject=subject, predicate=predicate, object_=obj)
        t = Table("Subject", "Predicate", "Object", "Confidence")
        for r in rows:
            t.add_row(r["subject"], r["predicate"], r["object"], f"{r['confidence']:.2f}")
        console.print(t if rows else "No triples.")

    @graph_app.command("query")
    def graph_query(subject: str):
        """Show all triples for a subject (neighbors)."""
        db.init()
        rows = repo.list_triples(subject=subject)
        t = Table("Subject", "Predicate", "Object", "Confidence")
        for r in rows:
            t.add_row(r["subject"], r["predicate"], r["object"], f"{r['confidence']:.2f}")
        console.print(t if rows else f"No triples for {subject}.")

    @graph_app.command("sync")
    def graph_sync():
        """Auto-populate the graph from accounts, categories and transactions."""
        db.init()
        from ..services.graph_service import sync_from_data
        counts = sync_from_data()
        console.print(f"[green]Graph synced:[/green] {counts['accounts']} accounts, "
                      f"{counts['merchants']} merchants, {counts['categories']} categories.")

    @graph_app.command("show")
    def graph_show(limit: int = typer.Option(50, "--limit", "-n", help="Max triples to show."),
                  subject: Optional[str] = typer.Option(None, "--subject", "-s", help="Filter by subject.")):
        """Pretty-print the graph grouped by subject."""
        db.init()
        rows = repo.list_triples(subject=subject)
        if not rows:
            console.print("No triples. Run [bold]summa graph sync[/bold] to populate.")
            return
        from collections import defaultdict
        groups = defaultdict(list)
        for r in rows[:limit]:
            groups[r["subject"]].append(r)
        for subj, rels in groups.items():
            console.print(f"[bold cyan]{subj}[/bold cyan]")
            for r in rels:
                console.print(f"  --{r['predicate']}--> {r['object']}  [dim](conf {r['confidence']:.2f})[/dim]")
        if len(rows) > limit:
            console.print(f"[dim]... and {len(rows)-limit} more (use --limit)[/dim]")

    @graph_app.command("clear")
    def graph_clear(confirm: bool = typer.Option(False, "--yes", "-y", help="Confirm clearing all triples.")):
        """Clear all graph triples."""
        db.init()
        if not confirm:
            console.print("Use --yes to confirm.")
            raise typer.Exit(1)
        with db.db() as conn:
            conn.execute("DELETE FROM graph_triples")
        console.print("[green]Graph cleared.[/green]")

    @graph_app.command("stats")
    def graph_stats():
        """Show graph statistics."""
        db.init()
        rows = repo.list_triples()
        subjects = {r["subject"] for r in rows}
        preds = {r["predicate"] for r in rows}
        console.print(f"Triples: {len(rows)} | Subjects: {len(subjects)} | Predicates: {len(preds)}")

    @graph_app.command("remove")
    def graph_remove(subject: str, predicate: str, obj: str):
        """Remove a triple."""
        db.init()
        if repo.delete_triple(subject, predicate, obj):
            console.print(f"[green]Removed:[/green] {subject} {predicate} {obj}")
        else:
            console.print(f"[red]Not found.[/red]")
            raise typer.Exit(1)
