"""
Search command for pyrite CLI.

Commands: search (with file-based fallback)
"""

import typer
from rich.console import Console
from rich.table import Table

from ..config import load_config
from ..storage.repository import KBRepository

console = Console()


def register_search_command(app: typer.Typer):
    """Register the search command on the given Typer app."""

    @app.command("search")
    def search(
        query: str = typer.Argument(..., help="Search query (FTS5 syntax supported)"),
        kb_name: str | None = typer.Option(None, "--kb", "-k", help="Search specific KB"),
        entry_type: str | None = typer.Option(None, "--type", "-t", help="Filter by type"),
        tag: str | None = typer.Option(None, "--tag", help="Filter by tag"),
        date_from: str | None = typer.Option(None, "--from", help="Events from date (YYYY-MM-DD)"),
        date_to: str | None = typer.Option(None, "--to", help="Events until date (YYYY-MM-DD)"),
        limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
        mode: str = typer.Option(
            None, "--mode", "-m", help="Search mode: keyword, semantic, hybrid"
        ),
        use_files: bool = typer.Option(False, "--files", help="Search files directly (skip index)"),
        expand: bool = typer.Option(False, "--expand", "-x", help="Use AI query expansion"),
        output_format: str = typer.Option(
            "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
        ),
    ):
        """
        Search across knowledge bases.

        Supports FTS5 query syntax:
        - Simple terms: miller immigration
        - Phrases: "family separation"
        - Boolean: miller AND immigration
        - Prefix: immigr*
        - Exclude: miller -bannon
        """
        config = load_config()

        if use_files:
            _search_files(config, query, kb_name, entry_type, limit)
            return

        from ..storage import PyriteDB

        try:
            db = PyriteDB(config.settings.index_path)

            if db.count_entries() == 0:
                console.print("[yellow]Index is empty. Building index...[/yellow]")
                from ..storage import IndexManager

                index_mgr = IndexManager(db, config)
                index_mgr.index_all()

            tags_list = [tag] if tag else None

            from ..services.search_service import SearchService

            search_svc = SearchService(db, settings=config.settings)
            search_mode = mode or config.settings.search_mode or "keyword"
            results = search_svc.search(
                query=query,
                kb_name=kb_name,
                entry_type=entry_type,
                tags=tags_list,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                mode=search_mode,
                expand=expand,
            )

            if not results:
                console.print("[yellow]No results found.[/yellow]")
                return

            if output_format != "rich":
                from ..formats import format_response

                resp_data = {"query": query, "count": len(results), "results": results}
                content, _ = format_response(resp_data, output_format)
                typer.echo(content)
                return

            table = Table(title=f"Search Results ({len(results)})")
            table.add_column("KB", style="cyan", width=12)
            table.add_column("Type", style="green", width=10)
            table.add_column("Title", width=40)
            table.add_column("Date", width=10)
            table.add_column("Snippet", width=50)

            for r in results:
                date = r.get("date", "")[:10] if r.get("date") else ""
                snippet = r.get("snippet", "")[:100] if r.get("snippet") else ""
                table.add_row(
                    r.get("kb_name", ""),
                    r.get("entry_type", ""),
                    r.get("title", "")[:40],
                    date,
                    snippet,
                )

            console.print(table)

        except Exception as e:
            console.print(f"[red]Search error:[/red] {e}")
            console.print("[dim]Falling back to file search...[/dim]")
            _search_files(config, query, kb_name, entry_type, limit)


def _search_files(config, query, kb_name, entry_type, limit):
    """File-based search fallback."""
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

    console.print(f"[dim]Searching for '{query}'...[/dim]")

    results = []
    for kb in kbs:
        if not kb.path.exists():
            continue

        repo = KBRepository(kb)
        for md_file in repo.list_files():
            try:
                content = md_file.read_text(encoding="utf-8")
                if query.lower() in content.lower():
                    entry = repo._load_entry(md_file)

                    if entry_type and entry.entry_type != entry_type:
                        continue

                    results.append((kb.name, entry, md_file))

                    if len(results) >= limit:
                        break
            except Exception:
                continue

        if len(results) >= limit:
            break

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(title=f"Search Results ({len(results)})")
    table.add_column("KB", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Title")
    table.add_column("ID", style="dim")

    for kb_name, entry, _path in results:
        table.add_row(kb_name, entry.entry_type, entry.title, entry.id)

    console.print(table)
