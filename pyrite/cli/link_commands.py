"""
Link management commands for pyrite CLI.

Commands: check
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


@links_app.command("check")
def links_check(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB to check links from"),
    limit: int = typer.Option(500, "--limit", help="Max missing targets to show"),
    detail: bool = typer.Option(False, "--detail", help="Show per-link breakdown"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
):
    """Check for broken links (links to missing targets).

    Shows missing targets sorted by how many entries reference them.
    Use --detail to see which entries contain each broken link.
    """
    from ..services.wikilink_service import WikilinkService

    config, db = get_config_and_db()
    svc = WikilinkService(config, db)
    targets = svc.check_links(kb_name=kb_name, limit=limit)

    total_refs = sum(t["ref_count"] for t in targets)

    formatted = _format_output(
        {
            "missing_targets": len(targets),
            "total_references": total_refs,
            "targets": targets,
        },
        output_format,
    )
    if formatted is not None:
        typer.echo(formatted)
        return

    if not targets:
        console.print("[green]No broken links found.[/green]")
        return

    console.print(
        f"\n[bold]Link Check:[/bold] {len(targets)} missing target(s),"
        f" {total_refs} reference(s)\n"
    )

    if detail:
        for t in targets:
            console.print(
                f"[bold]{t['target_id']}[/bold] ({t['target_kb']})"
                f" \u2014 {t['ref_count']} reference(s)"
            )
            for ref in t["references"]:
                rel = f" ({ref['relation']})" if ref.get("relation") else ""
                source = ref["source_id"]
                if ref["source_kb"] != t["target_kb"]:
                    source = f"{ref['source_kb']}/{source}"
                console.print(f"  \u2190 {source}{rel}")
            console.print()
    else:
        table = Table(show_lines=False)
        table.add_column("Missing Entry")
        table.add_column("KB")
        table.add_column("Refs", justify="right")
        table.add_column("Referenced By")

        for t in targets:
            ref_ids = [r["source_id"] for r in t["references"]]
            if len(ref_ids) > 3:
                ref_summary = ", ".join(ref_ids[:3]) + f" (+{len(ref_ids) - 3})"
            else:
                ref_summary = ", ".join(ref_ids)
            table.add_row(
                t["target_id"],
                t["target_kb"],
                str(t["ref_count"]),
                ref_summary,
            )

        console.print(table)
        if not detail:
            console.print(
                "\nRun with [bold]--detail[/bold] for per-link breakdown."
            )
