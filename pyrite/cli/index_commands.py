"""
Index management commands for pyrite CLI.

Commands: build, sync, stats, embed, health
"""

import logging

import typer
from rich.console import Console
from rich.table import Table

from ..utils.errors import cli_error
from .context import get_config_and_db

logger = logging.getLogger(__name__)

index_app = typer.Typer(help="Search index management")
console = Console()


def _format_output(data: dict, fmt: str) -> str | None:
    from .output import format_output

    return format_output(data, fmt)


@index_app.command("build")
def index_build(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB to index (all if omitted)"),
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
            # Submit rebuild for each KB (incl. `kb add` / DB-registered ones)
            job_ids = []
            for kb in config.all_kbs():
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
            cli_error(
                f"KB '{kb_name}' not found",
                error_code="KB_NOT_FOUND",
                suggestion="run `pyrite kb list` to see available KBs",
            )
        kbs = [kb]
    else:
        kbs = config.all_kbs()

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
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB to sync (all if omitted)"),
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
    # Surface malformed-frontmatter files as a summary instead of letting
    # per-file ScannerError tracebacks pollute stderr. Tier A 1080.
    malformed = results.get("malformed", [])
    if malformed:
        console.print(
            f"  [yellow]Malformed: {len(malformed)} file(s) skipped[/yellow]"
        )
        for entry in malformed[:5]:
            console.print(f"    [dim]• {entry['path']}[/dim]")
        if len(malformed) > 5:
            console.print(f"    [dim]… and {len(malformed) - 5} more[/dim]")

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
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB to embed (all if omitted)"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-embed all entries"),
):
    """Generate vector embeddings for semantic search."""
    from ..services.embedding_service import EmbeddingService, is_available

    if not is_available():
        cli_error(
            "sentence-transformers is not installed.",
            error_code="DEPENDENCY_MISSING",
            suggestion="install with: pip install pyrite[semantic]",
        )

    config, db = get_config_and_db()

    if not db.vec_available:
        cli_error(
            "sqlite-vec is not installed or failed to load.",
            error_code="DEPENDENCY_MISSING",
            suggestion="install with: pip install pyrite[semantic]",
        )

    # Check index has entries
    row = db._raw_conn.execute("SELECT COUNT(*) FROM entry").fetchone()
    if row[0] == 0:
        cli_error(
            "Index is empty.",
            error_code="INDEX_EMPTY",
            suggestion="run `pyrite index build` first",
        )

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
    if stats.get("truncated"):
        # Surface silent body-truncation count so operators know
        # how many entries had only a prefix embedded (Tier A r2100).
        console.print(
            f"  [yellow]Truncated: {stats['truncated']}[/yellow]"
            f" (body clipped to embedding model's char limit)"
        )
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

    broken_links = health.get("broken_links", 0)
    undeclared_types = health.get("undeclared_types", [])
    missing_required = health.get("missing_required_fields", [])
    subdirectory_mismatches = health.get("subdirectory_mismatches", [])
    malformed_frontmatter = health.get("malformed_frontmatter", [])
    invalid_statuses = health.get("invalid_statuses", [])
    is_unhealthy = (
        health["missing_files"]
        or health["unindexed_files"]
        or health["stale_entries"]
        or health.get("content_changed")
    )
    has_warning = (
        bool(broken_links)
        or bool(undeclared_types)
        or bool(missing_required)
        or bool(subdirectory_mismatches)
        or bool(malformed_frontmatter)
        or bool(invalid_statuses)
    )
    status = "unhealthy" if is_unhealthy else ("warning" if has_warning else "healthy")

    formatted = _format_output(
        {
            "status": status,
            "missing_files": len(health["missing_files"]),
            "unindexed_files": len(health["unindexed_files"]),
            "stale_entries": len(health["stale_entries"]),
            "content_changed": len(health.get("content_changed", [])),
            "broken_links": broken_links,
            "undeclared_types": undeclared_types,
            "missing_required_fields": missing_required,
            "subdirectory_mismatches": subdirectory_mismatches,
            "malformed_frontmatter": malformed_frontmatter,
            "invalid_statuses": invalid_statuses,
            "checks": health,
        },
        output_format,
    )
    if formatted is not None:
        typer.echo(formatted)
        return

    console.print("\n[bold]Index Health Check[/bold]\n")

    if not is_unhealthy and not has_warning:
        console.print("[green]✓ Index is healthy[/green]")
        return

    if not is_unhealthy and has_warning:
        console.print("[green]✓ Index is healthy[/green]")

    if broken_links:
        console.print(
            f"[yellow]⚠ {broken_links} broken link(s) found.[/yellow]"
            " Run 'pyrite links check' for details."
        )

    if undeclared_types:
        total = sum(row["count"] for row in undeclared_types)
        console.print(
            f"[yellow]⚠ {len(undeclared_types)} undeclared entry type(s)"
            f" across {total} entries — not in kb.yaml:[/yellow]"
        )
        for row in undeclared_types[:10]:
            console.print(
                f"  • {row['kb']}: type='{row['type']}' ({row['count']} entries)"
            )
        if len(undeclared_types) > 10:
            console.print(f"  ... and {len(undeclared_types) - 10} more")

    if missing_required:
        console.print(
            f"[yellow]⚠ {len(missing_required)} entries missing required fields:[/yellow]"
        )
        for row in missing_required[:10]:
            console.print(
                f"  • {row['kb']}/{row['id']} (type={row['type']}): missing {row['missing']}"
            )
        if len(missing_required) > 10:
            console.print(f"  ... and {len(missing_required) - 10} more")

    if subdirectory_mismatches:
        console.print(
            f"[yellow]⚠ {len(subdirectory_mismatches)} entries in the wrong"
            " subdirectory (writer hint, not enforced):[/yellow]"
        )
        for row in subdirectory_mismatches[:10]:
            console.print(
                f"  • {row['kb']}/{row['id']} (type={row['type']}):"
                f" expected '{row['declared_subdirectory']}/', found '{row['actual_path']}/'"
            )
        if len(subdirectory_mismatches) > 10:
            console.print(f"  ... and {len(subdirectory_mismatches) - 10} more")

    if malformed_frontmatter:
        console.print(
            f"[yellow]⚠ {len(malformed_frontmatter)} file(s) with malformed"
            " frontmatter (skipped — fix the YAML to index them):[/yellow]"
        )
        for row in malformed_frontmatter[:10]:
            console.print(f"  • {row['kb']}: {row['path']} — {row['error']}")
        if len(malformed_frontmatter) > 10:
            console.print(f"  ... and {len(malformed_frontmatter) - 10} more")

    if invalid_statuses:
        console.print(
            f"[yellow]⚠ {len(invalid_statuses)} entries with an invalid status"
            " (not in the type's declared enum):[/yellow]"
        )
        for row in invalid_statuses[:10]:
            allowed = ", ".join(row.get("allowed", [])) or "(see schema)"
            console.print(
                f"  • {row['kb']}/{row['id']} ({row['type']}):"
                f" status='{row['status']}' — allowed: {allowed}"
            )
        if len(invalid_statuses) > 10:
            console.print(f"  ... and {len(invalid_statuses) - 10} more")

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

    content_changed = health.get("content_changed", [])
    if content_changed:
        console.print(
            f"[yellow]Content changed, mtime unchanged ({len(content_changed)}):[/yellow]"
        )
        for item in content_changed[:10]:
            console.print(f"  • {item['kb']}/{item['id']}")
        if len(content_changed) > 10:
            console.print(f"  ... and {len(content_changed) - 10} more")

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
        cli_error(
            f"KB '{kb_name}' not found",
            error_code="KB_NOT_FOUND",
            suggestion="run `pyrite kb list` to see available KBs",
        )

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
            # Per-entry failure inside a batch: warn and continue, do NOT exit.
            console.print(f"[red]Failed to move {entry.id}:[/red] {e}")

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
