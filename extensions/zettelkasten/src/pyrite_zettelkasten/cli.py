"""Zettelkasten CLI commands."""

from datetime import UTC, datetime

import typer
from rich.console import Console
from rich.table import Table

from pyrite.config import load_config
from pyrite.schema import generate_entry_id
from pyrite.storage.database import PyriteDB

from .entry_types import LiteratureNoteEntry, ZettelEntry

zettel_app = typer.Typer(help="Zettelkasten knowledge management")
console = Console()


@zettel_app.command("new")
def zettel_new(
    title: str = typer.Argument(..., help="Note title"),
    zettel_type: str = typer.Option(
        "fleeting", "--type", "-t", help="Type: fleeting, literature, permanent, hub"
    ),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="Target KB"),
    source: str = typer.Option("", "--source", "-s", help="Source reference"),
):
    """Create a new zettel with the appropriate template."""
    from pyrite.storage.repository import KBRepository

    config = load_config()

    # Find target KB
    kb_config = None
    if kb_name:
        kb_config = config.get_kb(kb_name)
    else:
        # Find first KB that has zettel type configured
        for kb in config.knowledge_bases:
            kb_config = kb
            break

    if not kb_config:
        console.print("[red]Error:[/red] No KB found. Specify --kb.")
        raise typer.Exit(1)

    entry_id = generate_entry_id(title)
    now = datetime.now(UTC)

    if zettel_type == "literature":
        entry = LiteratureNoteEntry(
            id=entry_id,
            title=title,
            source_work=source,
            created_at=now,
            updated_at=now,
        )
    else:
        entry = ZettelEntry(
            id=entry_id,
            title=title,
            zettel_type=zettel_type,
            processing_stage="capture" if zettel_type == "fleeting" else "",
            source_ref=source,
            created_at=now,
            updated_at=now,
        )

    repo = KBRepository(kb_config)
    file_path = repo.save(entry)
    console.print(f"[green]Created {zettel_type} note:[/green] {file_path}")


@zettel_app.command("inbox")
def zettel_inbox(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB to search"),
):
    """List fleeting notes not yet fully processed (not at 'connect' stage)."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        results = db.search("*", limit=500)
        fleeting = []
        for r in results:
            if r.get("entry_type") != "zettel":
                if kb_name and r.get("kb_name") != kb_name:
                    continue
                continue
            if kb_name and r.get("kb_name") != kb_name:
                continue
            # Check metadata for zettel_type and processing_stage
            meta = r.get("metadata") or {}
            if isinstance(meta, str):
                import json

                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = {}
            zt = meta.get("zettel_type", r.get("zettel_type", ""))
            stage = meta.get("processing_stage", r.get("processing_stage", ""))
            if zt == "fleeting" and stage != "connect":
                fleeting.append({**r, "processing_stage": stage})

        if not fleeting:
            console.print("[dim]Inbox empty — all fleeting notes processed.[/dim]")
            return

        table = Table(title="Zettel Inbox")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Stage", style="yellow")
        table.add_column("KB", style="dim")

        for z in fleeting:
            table.add_row(
                z.get("id", ""),
                z.get("title", ""),
                z.get("processing_stage", "capture"),
                z.get("kb_name", ""),
            )

        console.print(table)
    finally:
        db.close()


@zettel_app.command("orphans")
def zettel_orphans(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB to search"),
):
    """Find notes with no incoming or outgoing links."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        orphans = db.get_orphans(kb_name=kb_name)

        if not orphans:
            console.print("[green]No orphan notes found.[/green]")
            return

        table = Table(title="Orphan Notes")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Type", style="yellow")
        table.add_column("KB", style="dim")

        for o in orphans:
            table.add_row(
                o.get("id", ""),
                o.get("title", ""),
                o.get("entry_type", ""),
                o.get("kb_name", ""),
            )

        console.print(table)
        console.print(f"\n[dim]{len(orphans)} orphan(s) found[/dim]")
    finally:
        db.close()


@zettel_app.command("maturity")
def zettel_maturity(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB to search"),
):
    """Show maturity distribution of zettels."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        results = db.search("*", limit=1000)
        counts = {"seed": 0, "sapling": 0, "evergreen": 0, "unknown": 0}
        total = 0

        for r in results:
            if r.get("entry_type") != "zettel":
                continue
            if kb_name and r.get("kb_name") != kb_name:
                continue
            meta = r.get("metadata") or {}
            if isinstance(meta, str):
                import json

                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = {}
            maturity = meta.get("maturity", r.get("maturity", "seed"))
            counts[maturity] = counts.get(maturity, 0) + 1
            total += 1

        if total == 0:
            console.print("[dim]No zettels found.[/dim]")
            return

        table = Table(title="Zettel Maturity Distribution")
        table.add_column("Maturity", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Percentage", justify="right")

        for level in ("seed", "sapling", "evergreen"):
            count = counts.get(level, 0)
            pct = (count / total * 100) if total > 0 else 0
            table.add_row(level, str(count), f"{pct:.0f}%")

        console.print(table)
        console.print(f"\n[dim]Total zettels: {total}[/dim]")
    finally:
        db.close()
