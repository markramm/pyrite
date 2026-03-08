"""
Index management commands for pyrite CLI.

Commands: build, sync, stats, embed, health
"""

import logging

import typer
from rich.console import Console
from rich.table import Table

from .context import get_config_and_db

logger = logging.getLogger(__name__)

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
    background: bool = typer.Option(False, "--background", help="Run in background thread"),
):
    """Build or rebuild the search index."""
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

    from ..storage import IndexManager

    config, db = get_config_and_db()

    if background:
        from ..services.index_worker import IndexWorker

        worker = IndexWorker(db, config)
        if kb_name:
            job_id = worker.submit_rebuild(kb_name)
        else:
            # Submit rebuild for each KB
            job_ids = []
            for kb in config.knowledge_bases:
                if kb.path.exists():
                    job_ids.append(worker.submit_rebuild(kb.name))
            console.print(f"[green]Submitted {len(job_ids)} rebuild job(s)[/green]")
            console.print("Use 'pyrite index jobs' to check progress.")
            return
        console.print(f"[green]Rebuild job submitted:[/green] {job_id}")
        console.print("Use 'pyrite index jobs' to check progress.")
        return

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
    background: bool = typer.Option(False, "--background", help="Run in background thread"),
):
    """Incremental sync: update index for changed files only."""
    from ..storage import IndexManager

    config, db = get_config_and_db()

    if background:
        from ..services.index_worker import IndexWorker

        worker = IndexWorker(db, config)
        job_id = worker.submit_sync(kb_name)
        console.print(f"[green]Sync job submitted:[/green] {job_id}")
        console.print("Use 'pyrite index jobs' to check progress.")
        return

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
        "json", "--format", help="Output format: json, rich, markdown, csv, yaml"
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
        "json", "--format", help="Output format: json, rich, markdown, csv, yaml"
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


@index_app.command("reconcile")
def index_reconcile(
    kb_name: str = typer.Argument(..., help="KB to reconcile"),
    apply: bool = typer.Option(False, "--apply", help="Execute moves (default is dry-run)"),
):
    """Move files to match their resolved subdirectory templates.

    Compares each entry's current file location against its template-resolved
    path. By default runs in dry-run mode. Use --apply to execute moves.
    """
    from ..storage.document_manager import DocumentManager
    from ..storage.index import IndexManager
    from ..storage.repository import KBRepository

    config, db = get_config_and_db()
    kb_config = config.get_kb(kb_name)
    if not kb_config:
        console.print(f"[red]Error:[/red] KB '{kb_name}' not found")
        raise typer.Exit(1)

    repo = KBRepository(kb_config)
    moves = []

    for entry, current_path in repo.list_entries():
        inferred_subdir = repo._infer_subdir(entry)
        expected_path = repo._get_file_path(entry.id, inferred_subdir)
        if current_path.resolve() != expected_path.resolve():
            moves.append((entry, current_path, expected_path))

    if not moves:
        console.print("[green]All files match their template paths.[/green]")
        return

    table = Table(title=f"{'[DRY RUN] ' if not apply else ''}Files to move")
    table.add_column("Entry ID", style="cyan")
    table.add_column("Current Path")
    table.add_column("Target Path")
    for entry, current, target in moves:
        try:
            current_rel = str(current.relative_to(kb_config.path))
        except ValueError:
            current_rel = str(current)
        try:
            target_rel = str(target.relative_to(kb_config.path))
        except ValueError:
            target_rel = str(target)
        table.add_row(entry.id, current_rel, target_rel)
    console.print(table)
    console.print(f"\nTotal: {len(moves)} file(s) to move")

    if not apply:
        console.print("\n[yellow]Dry run. Use --apply to execute moves.[/yellow]")
        return

    # Execute moves by re-saving each entry (triggers DocumentManager move logic)
    index_mgr = IndexManager(db, config)
    doc_mgr = DocumentManager(db, index_mgr)
    moved = 0
    for entry, _current_path, _target_path in moves:
        try:
            doc_mgr.save_entry(entry, kb_name, kb_config)
            moved += 1
        except Exception as e:
            console.print(f"[red]Error moving {entry.id}:[/red] {e}")

    console.print(f"\n[green]Moved {moved} file(s).[/green]")
    console.print("Run 'pyrite index sync' to update the index.")


@index_app.command("jobs")
def index_jobs():
    """List active and recent index jobs."""
    from ..services.index_worker import IndexWorker

    config, db = get_config_and_db()
    worker = IndexWorker(db, config)

    # Show recent jobs (active and completed)
    jobs = worker.get_recent_jobs()

    if not jobs:
        console.print("[dim]No index jobs found.[/dim]")
        return

    table = Table(title="Index Jobs")
    table.add_column("Job ID", style="cyan")
    table.add_column("KB")
    table.add_column("Operation")
    table.add_column("Status")
    table.add_column("Progress")
    table.add_column("Results")
    table.add_column("Created")

    for job in jobs:
        status_style = {
            "pending": "yellow",
            "running": "blue",
            "completed": "green",
            "failed": "red",
        }.get(job["status"], "")

        progress = ""
        if job["progress_total"]:
            progress = f"{job['progress_current']}/{job['progress_total']}"

        result_parts = []
        if job["added"]:
            result_parts.append(f"+{job['added']}")
        if job["updated"]:
            result_parts.append(f"~{job['updated']}")
        if job["removed"]:
            result_parts.append(f"-{job['removed']}")
        results_str = " ".join(result_parts) if result_parts else ""

        if job["error"]:
            results_str = job["error"][:40]

        table.add_row(
            job["job_id"],
            job["kb_name"] or "all",
            job["operation"],
            f"[{status_style}]{job['status']}[/{status_style}]",
            progress,
            results_str,
            job["created_at"][:19] if job["created_at"] else "",
        )

    console.print(table)
