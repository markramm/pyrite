"""
Link management commands for pyrite CLI.

Commands: broken, wanted
"""

import typer
from rich.console import Console
from rich.table import Table

from .context import get_config_and_db

links_app = typer.Typer(help="Link validation and inspection")
console = Console()


def _format_output(data: dict, fmt: str) -> str | None:
    """Format data using the format registry. Returns None for default (rich) output."""
    if fmt == "rich":
        return None
    from ..formats import format_response

    content, _ = format_response(data, fmt)
    return content


@links_app.command("broken")
def links_broken(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="Source KB to filter"),
    target_kb: str | None = typer.Option(None, "--target-kb", help="Target KB to filter"),
    limit: int = typer.Option(500, "--limit", help="Max results"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
):
    """Show broken links (links to missing targets)."""
    from ..services.wikilink_service import WikilinkService

    config, db = get_config_and_db()
    svc = WikilinkService(config, db)
    broken = svc.get_broken_links(kb_name=kb_name, target_kb=target_kb, limit=limit)

    formatted = _format_output(
        {"count": len(broken), "broken_links": broken},
        output_format,
    )
    if formatted is not None:
        typer.echo(formatted)
        return

    if not broken:
        console.print("[green]No broken links found.[/green]")
        return

    console.print(f"\n[bold]Broken Links ({len(broken)})[/bold]\n")
    table = Table(show_lines=False)
    table.add_column("Source KB")
    table.add_column("Source Entry")
    table.add_column("Target KB")
    table.add_column("Target (missing)")
    table.add_column("Relation")

    for link in broken:
        table.add_row(
            link["source_kb"],
            link["source_id"],
            link["target_kb"],
            link["target_id"],
            link.get("relation", ""),
        )

    console.print(table)


@links_app.command("wanted")
def links_wanted(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="Target KB to filter"),
    limit: int = typer.Option(100, "--limit", help="Max results"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
):
    """Show wanted pages (aggregated missing link targets)."""
    from ..services.wikilink_service import WikilinkService

    config, db = get_config_and_db()
    svc = WikilinkService(config, db)
    wanted = svc.get_wanted_pages(kb_name=kb_name, limit=limit)

    formatted = _format_output(
        {"count": len(wanted), "wanted_pages": wanted},
        output_format,
    )
    if formatted is not None:
        typer.echo(formatted)
        return

    if not wanted:
        console.print("[green]No wanted pages.[/green]")
        return

    console.print(f"\n[bold]Wanted Pages ({len(wanted)})[/bold]\n")
    table = Table(show_lines=False)
    table.add_column("Target ID")
    table.add_column("Target KB")
    table.add_column("Ref Count")
    table.add_column("Referenced By")

    for page in wanted:
        table.add_row(
            page["target_id"],
            page["target_kb"],
            str(page["ref_count"]),
            page.get("referenced_by", ""),
        )

    console.print(table)
