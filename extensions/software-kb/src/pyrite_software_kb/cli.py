"""Software KB CLI commands."""

import json

import typer
from rich.console import Console
from rich.table import Table

from pyrite.config import load_config
from pyrite.storage.database import PyriteDB

sw_app = typer.Typer(help="Software KB commands (ADRs, backlog, standards, components)")
console = Console()


def _query_entries(db: PyriteDB, entry_type: str, kb_name: str | None = None) -> list[dict]:
    """Query entries by type, returning rows with parsed metadata."""
    query = "SELECT * FROM entry WHERE entry_type = ?"
    params: list = [entry_type]
    if kb_name:
        query += " AND kb_name = ?"
        params.append(kb_name)
    query += " ORDER BY created_at DESC"
    rows = db._raw_conn.execute(query, params).fetchall()

    results = []
    for row in rows:
        item = dict(row)
        meta = {}
        if row["metadata"]:
            try:
                meta = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                pass
        item["_meta"] = meta
        results.append(item)
    return results


def _json_output(items: list[dict]) -> None:
    """Print items as compact JSON to stdout."""
    print(json.dumps(items, separators=(",", ":"), default=str))


@sw_app.command("adrs")
def sw_adrs(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """List Architecture Decision Records."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "adr", kb_name)

        if status:
            rows = [r for r in rows if r["_meta"].get("status", "proposed") == status]

        if not rows:
            if fmt == "json":
                _json_output([])
            else:
                console.print("[dim]No ADRs found.[/dim]")
            return

        if fmt == "json":
            _json_output([
                {
                    "adr_number": r["_meta"].get("adr_number", ""),
                    "title": r["title"],
                    "status": r["_meta"].get("status", "proposed"),
                    "date": r["_meta"].get("date", ""),
                }
                for r in rows
            ])
            return

        table = Table(title="Architecture Decision Records")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Title")
        table.add_column("Status", style="yellow")
        table.add_column("Date", style="dim")

        for row in rows:
            meta = row["_meta"]
            num = str(meta.get("adr_number", ""))
            table.add_row(
                num,
                row["title"],
                meta.get("status", "proposed"),
                meta.get("date", ""),
            )

        console.print(table)
    finally:
        db.close()


@sw_app.command("new-adr")
def sw_new_adr(
    title: str = typer.Argument(..., help="ADR title"),
    status: str = typer.Option("proposed", "--status", "-s", help="Initial status"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
):
    """Create a new ADR with the next sequential number."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "adr", kb_name)
        max_num = 0
        for row in rows:
            num = row["_meta"].get("adr_number", 0)
            if isinstance(num, int) and num > max_num:
                max_num = num
        next_num = max_num + 1

        console.print(f"[green]ADR-{next_num:04d}:[/green] {title}")
        console.print(f"  Status: [yellow]{status}[/yellow]")
        console.print(
            f"[dim]Create file: adrs/{next_num:04d}-{title.lower().replace(' ', '-')}.md[/dim]"
        )
        console.print(
            "[dim]Add frontmatter: type: adr, adr_number: " f"{next_num}, status: {status}[/dim]"
        )
    finally:
        db.close()


@sw_app.command("backlog")
def sw_backlog(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    priority: str | None = typer.Option(None, "--priority", "-p", help="Filter by priority"),
    kind: str | None = typer.Option(None, "--kind", "-t", help="Filter by kind"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """List backlog items."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "backlog_item", kb_name)

        if status:
            rows = [r for r in rows if r["_meta"].get("status", "proposed") == status]
        if priority:
            rows = [r for r in rows if r["_meta"].get("priority", "medium") == priority]
        if kind:
            rows = [r for r in rows if r["_meta"].get("kind", "") == kind]

        if not rows:
            if fmt == "json":
                _json_output([])
            else:
                console.print("[dim]No backlog items found.[/dim]")
            return

        if fmt == "json":
            _json_output([
                {
                    "id": r["id"],
                    "title": r["title"],
                    "kind": r["_meta"].get("kind", ""),
                    "status": r["_meta"].get("status", "proposed"),
                    "priority": r["_meta"].get("priority", "medium"),
                    "effort": r["_meta"].get("effort", ""),
                }
                for r in rows
            ])
            return

        table = Table(title="Backlog")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Kind", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Priority", style="red")
        table.add_column("Effort", style="dim")

        for row in rows:
            meta = row["_meta"]
            table.add_row(
                row["id"][:12],
                row["title"],
                meta.get("kind", ""),
                meta.get("status", "proposed"),
                meta.get("priority", "medium"),
                meta.get("effort", ""),
            )

        console.print(table)
    finally:
        db.close()


@sw_app.command("standards")
def sw_standards(
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """List coding standards and conventions."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "standard", kb_name)

        if category:
            rows = [r for r in rows if r["_meta"].get("category", "") == category]

        if not rows:
            if fmt == "json":
                _json_output([])
            else:
                console.print("[dim]No standards found.[/dim]")
            return

        if fmt == "json":
            _json_output([
                {
                    "title": r["title"],
                    "category": r["_meta"].get("category", ""),
                    "enforced": bool(r["_meta"].get("enforced")),
                }
                for r in rows
            ])
            return

        table = Table(title="Standards")
        table.add_column("Title")
        table.add_column("Category", style="blue")
        table.add_column("Enforced", style="yellow")

        for row in rows:
            meta = row["_meta"]
            enforced = "Yes" if meta.get("enforced") else "No"
            table.add_row(row["title"], meta.get("category", ""), enforced)

        console.print(table)
    finally:
        db.close()


@sw_app.command("components")
def sw_components(
    kind: str | None = typer.Option(None, "--kind", "-t", help="Filter by kind"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """List component documentation."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "component", kb_name)

        if kind:
            rows = [r for r in rows if r["_meta"].get("kind", "") == kind]

        if not rows:
            if fmt == "json":
                _json_output([])
            else:
                console.print("[dim]No components found.[/dim]")
            return

        if fmt == "json":
            _json_output([
                {
                    "title": r["title"],
                    "kind": r["_meta"].get("kind", ""),
                    "path": r["_meta"].get("path", ""),
                    "owner": r["_meta"].get("owner", ""),
                }
                for r in rows
            ])
            return

        table = Table(title="Components")
        table.add_column("Title")
        table.add_column("Kind", style="blue")
        table.add_column("Path", style="dim")
        table.add_column("Owner", style="cyan")

        for row in rows:
            meta = row["_meta"]
            table.add_row(
                row["title"],
                meta.get("kind", ""),
                meta.get("path", ""),
                meta.get("owner", ""),
            )

        console.print(table)
    finally:
        db.close()
