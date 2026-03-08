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
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """List Architecture Decision Records."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "adr", kb_name)

        if status:
            rows = [r for r in rows if (r.get("status") or r["_meta"].get("status", "proposed")) == status]

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
                    "status": r.get("status") or r["_meta"].get("status", "proposed"),
                    "date": r.get("date") or r["_meta"].get("date", ""),
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
                row.get("status") or meta.get("status", "proposed"),
                row.get("date") or meta.get("date", ""),
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
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """List backlog items."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "backlog_item", kb_name)

        if status:
            rows = [r for r in rows if (r.get("status") or r["_meta"].get("status", "proposed")) == status]
        if priority:
            rows = [r for r in rows if (r.get("priority") or r["_meta"].get("priority", "medium")) == priority]
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
                    "status": r.get("status") or r["_meta"].get("status", "proposed"),
                    "priority": r.get("priority") or r["_meta"].get("priority", "medium"),
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
                row.get("status") or meta.get("status", "proposed"),
                row.get("priority") or meta.get("priority", "medium"),
                meta.get("effort", ""),
            )

        console.print(table)
    finally:
        db.close()


@sw_app.command("standards")
def sw_standards(
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """List all standards (standard + programmatic_validation + development_convention). [deprecated: use validations/conventions]"""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = []
        for et in ("standard", "programmatic_validation", "development_convention"):
            rows.extend(_query_entries(db, et, kb_name))

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
                    "type": r["entry_type"],
                    "category": r["_meta"].get("category", ""),
                    "enforced": bool(r["_meta"].get("enforced")),
                }
                for r in rows
            ])
            return

        table = Table(title="Standards")
        table.add_column("Title")
        table.add_column("Type", style="magenta")
        table.add_column("Category", style="blue")
        table.add_column("Enforced", style="yellow")

        for row in rows:
            meta = row["_meta"]
            enforced = "Yes" if meta.get("enforced") else "No"
            table.add_row(row["title"], row["entry_type"], meta.get("category", ""), enforced)

        console.print(table)
    finally:
        db.close()


@sw_app.command("validations")
def sw_validations(
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """List programmatic validations (automated checks)."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "programmatic_validation", kb_name)

        if category:
            rows = [r for r in rows if r["_meta"].get("category", "") == category]

        if not rows:
            if fmt == "json":
                _json_output([])
            else:
                console.print("[dim]No programmatic validations found.[/dim]")
            return

        if fmt == "json":
            _json_output([
                {
                    "title": r["title"],
                    "category": r["_meta"].get("category", ""),
                    "check_command": r["_meta"].get("check_command", ""),
                    "pass_criteria": r["_meta"].get("pass_criteria", ""),
                }
                for r in rows
            ])
            return

        table = Table(title="Programmatic Validations")
        table.add_column("Title")
        table.add_column("Category", style="blue")
        table.add_column("Check Command", style="green")

        for row in rows:
            meta = row["_meta"]
            table.add_row(row["title"], meta.get("category", ""), meta.get("check_command", ""))

        console.print(table)
    finally:
        db.close()


@sw_app.command("conventions")
def sw_conventions(
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """List development conventions (judgment-based guidance)."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "development_convention", kb_name)

        if category:
            rows = [r for r in rows if r["_meta"].get("category", "") == category]

        if not rows:
            if fmt == "json":
                _json_output([])
            else:
                console.print("[dim]No development conventions found.[/dim]")
            return

        if fmt == "json":
            _json_output([
                {
                    "title": r["title"],
                    "category": r["_meta"].get("category", ""),
                }
                for r in rows
            ])
            return

        table = Table(title="Development Conventions")
        table.add_column("Title")
        table.add_column("Category", style="blue")

        for row in rows:
            meta = row["_meta"]
            table.add_row(row["title"], meta.get("category", ""))

        console.print(table)
    finally:
        db.close()


@sw_app.command("migrate-standards")
def sw_migrate_standards(
    apply: bool = typer.Option(False, "--apply", help="Actually apply changes (default: dry run)"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name to scope migration"),
):
    """Migrate type:standard entries to programmatic_validation or development_convention."""
    import re
    from pathlib import Path

    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "standard", kb_name)

        if not rows:
            console.print("[dim]No standard entries to migrate.[/dim]")
            return

        validations = []
        conventions = []

        for row in rows:
            meta = row["_meta"]
            enforced = bool(meta.get("enforced", False))
            if enforced:
                validations.append(row)
            else:
                conventions.append(row)

        console.print(f"Found [cyan]{len(rows)}[/cyan] standard entries:")
        console.print(f"  [green]{len(validations)}[/green] enforced -> programmatic_validation")
        console.print(f"  [blue]{len(conventions)}[/blue] non-enforced -> development_convention")

        if not apply:
            console.print("\n[yellow]Dry run — pass --apply to migrate.[/yellow]")
            return

        migrated = 0
        for row in rows:
            file_path = row.get("file_path") or row.get("source_path", "")
            if not file_path:
                console.print(f"  [red]Skip[/red] {row['title']}: no file_path")
                continue

            path = Path(file_path)
            if not path.exists():
                console.print(f"  [red]Skip[/red] {row['title']}: file not found at {path}")
                continue

            content = path.read_text()
            meta = row["_meta"]
            enforced = bool(meta.get("enforced", False))

            if enforced:
                new_type = "programmatic_validation"
                new_dir_name = "validations"
            else:
                new_type = "development_convention"
                new_dir_name = "conventions"

            # Replace type field in frontmatter
            content = re.sub(r'^type:\s*standard\s*$', f'type: {new_type}', content, flags=re.MULTILINE)

            # Remove enforced field
            content = re.sub(r'^enforced:\s*(true|false)\s*\n', '', content, flags=re.MULTILINE | re.IGNORECASE)

            # Write back
            path.write_text(content)

            # Move file to new subdirectory if parent is standards/
            if path.parent.name == "standards":
                new_dir = path.parent.parent / new_dir_name
                new_dir.mkdir(parents=True, exist_ok=True)
                new_path = new_dir / path.name
                path.rename(new_path)
                console.print(f"  [green]Migrated[/green] {row['title']} -> {new_path}")
            else:
                console.print(f"  [green]Migrated[/green] {row['title']} (type updated in place)")

            migrated += 1

        console.print(f"\n[green]{migrated}[/green] entries migrated.")
        console.print("[dim]Run `pyrite index sync` to update the index.[/dim]")
    finally:
        db.close()


@sw_app.command("components")
def sw_components(
    kind: str | None = typer.Option(None, "--kind", "-t", help="Filter by kind"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
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
