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

    @graph_app.command("remove")
    def graph_remove(subject: str, predicate: str, obj: str):
        """Remove a triple."""
        db.init()
        if repo.delete_triple(subject, predicate, obj):
            console.print(f"[green]Removed:[/green] {subject} {predicate} {obj}")
        else:
            console.print(f"[red]Not found.[/red]")
            raise typer.Exit(1)
