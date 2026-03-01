"""
Index management commands for pyrite CLI.

Commands: build, sync, stats, embed, health
"""

import logging

import typer
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

from .context import get_config_and_db

index_app = typer.Typer(help="Search index management")
console = Console()


def _format_output(data: dict, fmt: str) -> str | None:
    """Format data using the format registry. Returns None for default (rich) output."""
    if fmt == "rich":
        return None
    from ..formats import format_response

    content, _ = format_response(data, fmt)
    return content


@index_app.command("build")
def index_build(
    kb_name: str | None = typer.Argument(None, help="KB to index (all if omitted)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force full reindex"),
    with_attribution: bool = typer.Option(
        False, "--with-attribution", help="Extract git history for attribution"
    ),
    no_embed: bool = typer.Option(False, "--no-embed", help="Skip auto-embedding after build"),
):
    """Build or rebuild the search index."""
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

    from ..storage import IndexManager

    config, db = get_config_and_db()
    index_mgr = IndexManager(db, config)

    if kb_name:
        kb = config.get_kb(kb_name)
        if not kb:
            console.print(f"[red]Error:[/red] KB '{kb_name}' not found")
            raise typer.Exit(1)
        kbs = [kb]
    else:
        kbs = config.knowledge_bases

    if not kbs:
        console.print("[yellow]No knowledge bases configured.[/yellow]")
        return

    git_service = None
    if with_attribution:
        from ..services.git_service import GitService

        git_service = GitService()
        console.print("[dim]Building index with git attribution...[/dim]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        for kb in kbs:
            if not kb.path.exists():
                console.print(f"[yellow]Skipping {kb.name}: path does not exist[/yellow]")
                continue

            task = progress.add_task(f"Indexing {kb.name}...", total=None)

            def make_progress_callback(task_id):
                def update_progress(current: int, total: int):
                    progress.update(task_id, completed=current, total=total)

                return update_progress

            if with_attribution and git_service:
                count = index_mgr.index_with_attribution(
                    kb.name, git_service, progress_callback=make_progress_callback(task)
                )
            else:
                count = index_mgr.index_kb(kb.name, make_progress_callback(task))
            progress.update(task, description=f"[green]✓[/green] {kb.name}: {count} entries")

    console.print("\n[green]Index build complete.[/green]")

    # Auto-embed after build if embeddings are available
    if not no_embed:
        try:
            from ..services.embedding_service import EmbeddingService, is_available

            if is_available() and db.vec_available:
                console.print("[dim]Generating embeddings...[/dim]")
                svc = EmbeddingService(db, model_name=config.settings.embedding_model)
                stats = svc.embed_all(kb_name=kb_name, force=force)
                if stats["embedded"] > 0:
                    console.print(
                        f"[green]Embedded {stats['embedded']} entries[/green] "
                        f"(skipped {stats['skipped']})"
                    )
        except Exception:
            logger.debug("Embedding not available, skipping")


@index_app.command("sync")
def index_sync(
    kb_name: str | None = typer.Argument(None, help="KB to sync (all if omitted)"),
    no_embed: bool = typer.Option(False, "--no-embed", help="Skip auto-embedding after sync"),
):
    """Incremental sync: update index for changed files only."""
    from ..storage import IndexManager

    config, db = get_config_and_db()
    index_mgr = IndexManager(db, config)

    results = index_mgr.sync_incremental(kb_name)

    console.print("[green]Sync complete:[/green]")
    console.print(f"  Added: {results['added']}")
    console.print(f"  Updated: {results['updated']}")
    console.print(f"  Removed: {results['removed']}")

    # Auto-embed new/updated entries if embeddings are available
    changed = results["added"] + results["updated"]
    if changed > 0 and not no_embed:
        try:
            from ..services.embedding_service import EmbeddingService, is_available

            if is_available() and db.vec_available:
                svc = EmbeddingService(db, model_name=config.settings.embedding_model)
                stats = svc.embed_all(kb_name=kb_name)
                if stats["embedded"] > 0:
                    console.print(f"  Embedded: {stats['embedded']}")
        except Exception:
            logger.debug("Embedding not available, skipping")


@index_app.command("stats")
def index_stats(
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """Show index statistics."""
    from ..storage import IndexManager

    config, db = get_config_and_db()
    index_mgr = IndexManager(db, config)

    stats = index_mgr.get_index_stats()

    formatted = _format_output(stats, output_format)
    if formatted is not None:
        typer.echo(formatted)
        return

    console.print("\n[bold]Index Statistics[/bold]\n")
    console.print(f"Total entries: {stats['total_entries']}")
    console.print(f"Total tags: {stats['total_tags']}")
    console.print(f"Total links: {stats['total_links']}")

    if stats["kbs"]:
        console.print("\n[bold]Knowledge Bases:[/bold]")
        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Entries", justify="right")
        table.add_column("Last Indexed")

        for name, kb_stats in stats["kbs"].items():
            table.add_row(
                name,
                kb_stats.get("kb_type", "-"),
                str(kb_stats.get("actual_count", 0)),
                kb_stats.get("last_indexed", "-")[:19] if kb_stats.get("last_indexed") else "-",
            )
        console.print(table)


@index_app.command("embed")
def index_embed(
    kb_name: str | None = typer.Argument(None, help="KB to embed (all if omitted)"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-embed all entries"),
):
    """Generate vector embeddings for semantic search."""
    from ..services.embedding_service import EmbeddingService, is_available

    if not is_available():
        console.print("[red]Error:[/red] sentence-transformers is not installed.")
        console.print("Install with: pip install pyrite[semantic]")
        raise typer.Exit(1)

    config, db = get_config_and_db()

    if not db.vec_available:
        console.print("[red]Error:[/red] sqlite-vec is not installed or failed to load.")
        console.print("Install with: pip install pyrite[semantic]")
        raise typer.Exit(1)

    # Check index has entries
    row = db._raw_conn.execute("SELECT COUNT(*) FROM entry").fetchone()
    if row[0] == 0:
        console.print("[yellow]Index is empty. Run 'pyrite index build' first.[/yellow]")
        raise typer.Exit(1)

    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

    svc = EmbeddingService(db, model_name=config.settings.embedding_model)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Embedding entries...", total=None)

        def update_progress(current: int, total: int):
            progress.update(task, completed=current, total=total)

        stats = svc.embed_all(
            kb_name=kb_name,
            force=force,
            progress_callback=update_progress,
        )

    console.print("\n[green]Embedding complete.[/green]")
    console.print(f"  Embedded: {stats['embedded']}")
    console.print(f"  Skipped: {stats['skipped']}")
    if stats["errors"]:
        console.print(f"  [red]Errors: {stats['errors']}[/red]")


@index_app.command("health")
def index_health(
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """Check index health and consistency."""
    from ..storage import IndexManager

    config, db = get_config_and_db()
    index_mgr = IndexManager(db, config)

    health = index_mgr.check_health()

    formatted = _format_output(
        {
            "status": "healthy"
            if (
                not health["missing_files"]
                and not health["unindexed_files"]
                and not health["stale_entries"]
            )
            else "unhealthy",
            "missing_files": len(health["missing_files"]),
            "unindexed_files": len(health["unindexed_files"]),
            "stale_entries": len(health["stale_entries"]),
            "checks": health,
        },
        output_format,
    )
    if formatted is not None:
        typer.echo(formatted)
        return

    console.print("\n[bold]Index Health Check[/bold]\n")

    if (
        not health["missing_files"]
        and not health["unindexed_files"]
        and not health["stale_entries"]
    ):
        console.print("[green]✓ Index is healthy[/green]")
        return

    if health["missing_files"]:
        console.print(f"[red]Missing files ({len(health['missing_files'])}):[/red]")
        for item in health["missing_files"][:10]:
            console.print(f"  • {item['kb']}/{item['id']}")
        if len(health["missing_files"]) > 10:
            console.print(f"  ... and {len(health['missing_files']) - 10} more")

    if health["unindexed_files"]:
        console.print(f"[yellow]Unindexed files ({len(health['unindexed_files'])}):[/yellow]")
        for item in health["unindexed_files"][:10]:
            console.print(f"  • {item['kb']}/{item['id']}")
        if len(health["unindexed_files"]) > 10:
            console.print(f"  ... and {len(health['unindexed_files']) - 10} more")

    if health["stale_entries"]:
        console.print(f"[yellow]Stale entries ({len(health['stale_entries'])}):[/yellow]")
        for item in health["stale_entries"][:10]:
            console.print(f"  • {item['kb']}/{item['id']}")
        if len(health["stale_entries"]) > 10:
            console.print(f"  ... and {len(health['stale_entries']) - 10} more")

    console.print("\nRun 'pyrite index sync' to fix issues.")
