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
            rows = [
                r
                for r in rows
                if (r.get("status") or r["_meta"].get("status", "proposed")) == status
            ]

        if not rows:
            if fmt == "json":
                _json_output([])
            else:
                console.print("[dim]No ADRs found.[/dim]")
            return

        if fmt == "json":
            _json_output(
                [
                    {
                        "adr_number": r["_meta"].get("adr_number", ""),
                        "title": r["title"],
                        "status": r.get("status") or r["_meta"].get("status", "proposed"),
                        "date": r.get("date") or r["_meta"].get("date", ""),
                    }
                    for r in rows
                ]
            )
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
    from datetime import date
    from pathlib import Path

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

        slug = title.lower().replace(" ", "-")
        filename = f"{next_num:04d}-{slug}.md"
        today = date.today().isoformat()

        # Resolve KB path for file creation
        kb_path = None
        if kb_name:
            kb_conf = config.get_kb(kb_name)
            if kb_conf:
                kb_path = kb_conf.path
        if kb_path is None:
            kb_path = Path(".")

        adrs_dir = kb_path / "adrs"
        adrs_dir.mkdir(parents=True, exist_ok=True)
        file_path = adrs_dir / filename

        # Build the ADR file content
        content = (
            "---\n"
            f"id: adr-{next_num:04d}\n"
            "type: adr\n"
            f'title: "{title}"\n'
            f"adr_number: {next_num}\n"
            f"status: {status}\n"
            f"date: {today}\n"
            "---\n"
            "\n"
            f"# ADR-{next_num:04d}: {title}\n"
            "\n"
            "## Context\n"
            "\n"
            "TODO: What is the issue that we're seeing that is motivating this decision or change?\n"
            "\n"
            "## Decision\n"
            "\n"
            "TODO: What is the change that we're proposing and/or doing?\n"
            "\n"
            "## Consequences\n"
            "\n"
            "TODO: What becomes easier or more difficult to do because of this change?\n"
        )

        file_path.write_text(content)

        console.print(f"[green]Created ADR-{next_num:04d}:[/green] {title}")
        console.print(f"  File: [cyan]{file_path}[/cyan]")
        console.print(f"  Status: [yellow]{status}[/yellow]")
        console.print("[dim]Run `pyrite index sync` to update the index.[/dim]")
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
            rows = [
                r
                for r in rows
                if (r.get("status") or r["_meta"].get("status", "proposed")) == status
            ]
        if priority:
            rows = [
                r
                for r in rows
                if (r.get("priority") or r["_meta"].get("priority", "medium")) == priority
            ]
        if kind:
            rows = [r for r in rows if r["_meta"].get("kind", "") == kind]

        if not rows:
            if fmt == "json":
                _json_output([])
            else:
                console.print("[dim]No backlog items found.[/dim]")
            return

        if fmt == "json":
            _json_output(
                [
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "kind": r["_meta"].get("kind", ""),
                        "status": r.get("status") or r["_meta"].get("status", "proposed"),
                        "priority": r.get("priority") or r["_meta"].get("priority", "medium"),
                        "effort": r["_meta"].get("effort", ""),
                    }
                    for r in rows
                ]
            )
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
            _json_output(
                [
                    {
                        "title": r["title"],
                        "type": r["entry_type"],
                        "category": r["_meta"].get("category", ""),
                        "enforced": bool(r["_meta"].get("enforced")),
                    }
                    for r in rows
                ]
            )
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
            _json_output(
                [
                    {
                        "title": r["title"],
                        "category": r["_meta"].get("category", ""),
                        "check_command": r["_meta"].get("check_command", ""),
                        "pass_criteria": r["_meta"].get("pass_criteria", ""),
                    }
                    for r in rows
                ]
            )
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
            _json_output(
                [
                    {
                        "title": r["title"],
                        "category": r["_meta"].get("category", ""),
                    }
                    for r in rows
                ]
            )
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
            content = re.sub(
                r"^type:\s*standard\s*$", f"type: {new_type}", content, flags=re.MULTILINE
            )

            # Remove enforced field
            content = re.sub(
                r"^enforced:\s*(true|false)\s*\n", "", content, flags=re.MULTILINE | re.IGNORECASE
            )

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


@sw_app.command("milestones")
def sw_milestones(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """List milestones with completion progress."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "milestone", kb_name)

        if status:
            rows = [r for r in rows if r["_meta"].get("status", "open") == status]

        if not rows:
            if fmt == "json":
                _json_output([])
            else:
                console.print("[dim]No milestones found.[/dim]")
            return

        # Compute completion for each milestone
        results = []
        for row in rows:
            meta = row["_meta"]
            linked = db.get_outlinks(row["id"], row.get("kb_name", ""))
            total = 0
            completed = 0
            for link in linked:
                if link.get("entry_type") == "backlog_item":
                    total += 1
                    link_meta = {}
                    if link.get("metadata"):
                        try:
                            link_meta = (
                                json.loads(link["metadata"])
                                if isinstance(link["metadata"], str)
                                else link.get("metadata", {})
                            )
                        except (json.JSONDecodeError, TypeError):
                            pass
                    link_status = link.get("status") or link_meta.get("status", "proposed")
                    if link_status == "done":
                        completed += 1
            pct = round(completed / total * 100) if total > 0 else 0
            results.append(
                {
                    "title": row["title"],
                    "status": row.get("status") or meta.get("status", "open"),
                    "total_items": total,
                    "completed_items": completed,
                    "completion_pct": pct,
                }
            )

        if fmt == "json":
            _json_output(results)
            return

        table = Table(title="Milestones")
        table.add_column("Title")
        table.add_column("Status", style="yellow")
        table.add_column("Progress", style="green")

        for r in results:
            progress = f"{r['completed_items']}/{r['total_items']} ({r['completion_pct']}%)"
            table.add_row(r["title"], r["status"], progress)

        console.print(table)
    finally:
        db.close()


@sw_app.command("board")
def sw_board_cmd(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """View kanban board with backlog items grouped by lane."""
    from pathlib import Path

    from .board import load_board_config

    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        # Load board config
        if kb_name:
            kb_conf = config.get_kb(kb_name)
            board_config = (
                load_board_config(kb_conf.path) if kb_conf else load_board_config(Path("."))
            )
        else:
            board_config = load_board_config(Path("."))

        rows = _query_entries(db, "backlog_item", kb_name)

        # Build status→lane mapping
        status_to_lane: dict[str, int] = {}
        for i, lane in enumerate(board_config["lanes"]):
            for s in lane["statuses"]:
                status_to_lane[s] = i

        # Group items
        lane_items: dict[int, list] = {i: [] for i in range(len(board_config["lanes"]))}
        for row in rows:
            meta = row["_meta"]
            item_status = row.get("status") or meta.get("status", "proposed")
            lane_idx = status_to_lane.get(item_status)
            if lane_idx is not None:
                lane_items[lane_idx].append(row)

        lanes = []
        for i, lane_def in enumerate(board_config["lanes"]):
            items = lane_items.get(i, [])
            wip_limit = lane_def.get("wip_limit")
            lane: dict = {
                "name": lane_def["name"],
                "count": len(items),
            }
            if wip_limit is not None:
                lane["wip_limit"] = wip_limit
                lane["over_limit"] = len(items) > wip_limit
            lanes.append(lane)

        if fmt == "json":
            _json_output({"lanes": lanes, "wip_policy": board_config.get("wip_policy", "warn")})
            return

        table = Table(title="Board")
        table.add_column("Lane")
        table.add_column("Items", justify="right")
        table.add_column("WIP Limit", justify="right")
        table.add_column("Status", style="yellow")

        for lane in lanes:
            wip_str = str(lane.get("wip_limit", "")) if "wip_limit" in lane else "-"
            status_str = ""
            if lane.get("over_limit"):
                status_str = "[red]OVER LIMIT[/red]"
            elif "wip_limit" in lane:
                status_str = "[green]OK[/green]"
            table.add_row(lane["name"], str(lane["count"]), wip_str, status_str)

        console.print(table)
    finally:
        db.close()


@sw_app.command("review-queue")
def sw_review_queue(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """View items in review status, sorted by wait time."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "backlog_item", kb_name)

        # Filter to review status, sort by updated_at ascending (longest waiting first)
        review_items = []
        for r in rows:
            status = r.get("status") or r["_meta"].get("status", "proposed")
            if status == "review":
                review_items.append(r)
        review_items.sort(key=lambda r: r.get("updated_at", "") or "")

        if not review_items:
            if fmt == "json":
                _json_output([])
            else:
                console.print("[dim]No items in review.[/dim]")
            return

        if fmt == "json":
            _json_output(
                [
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "priority": r.get("priority") or r["_meta"].get("priority", "medium"),
                        "assignee": r.get("assignee") or r["_meta"].get("assignee", ""),
                        "updated_at": str(r.get("updated_at", "")),
                    }
                    for r in review_items
                ]
            )
            return

        table = Table(title="Review Queue")
        table.add_column("Title")
        table.add_column("Priority", style="red")
        table.add_column("Assignee", style="cyan")
        table.add_column("Waiting Since", style="dim")

        for row in review_items:
            meta = row["_meta"]
            table.add_row(
                row["title"],
                row.get("priority") or meta.get("priority", "medium"),
                row.get("assignee") or meta.get("assignee", ""),
                str(row.get("updated_at", "")),
            )

        console.print(table)
    finally:
        db.close()


@sw_app.command("claim")
def sw_claim(
    item_id: str = typer.Argument(..., help="Backlog item ID"),
    assignee: str = typer.Option(..., "--assignee", "-a", help="Who is claiming the item"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
):
    """Claim a backlog item: transition to in_progress and set assignee."""
    from pyrite.services.kb_service import KBService

    from .workflows import BACKLOG_WORKFLOW, can_transition, get_allowed_transitions

    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "backlog_item", kb_name)
        match = [r for r in rows if r["id"] == item_id]
        if not match:
            console.print(f"[red]Error:[/red] Backlog item '{item_id}' not found.")
            raise typer.Exit(1)

        row = match[0]
        current_status = row.get("status") or row["_meta"].get("status", "proposed")
        item_kb = row.get("kb_name", kb_name or "")

        if not can_transition(BACKLOG_WORKFLOW, current_status, "in_progress", "write"):
            allowed = get_allowed_transitions(BACKLOG_WORKFLOW, current_status, "write")
            targets = [t["to"] for t in allowed]
            console.print(
                f"[red]Error:[/red] Cannot transition from '{current_status}' to 'in_progress'. "
                f"Allowed: {', '.join(targets) or 'none'}"
            )
            raise typer.Exit(1)

        svc = KBService(config, db)
        result = svc.claim_entry(
            item_id,
            item_kb,
            assignee,
            from_status=current_status,
            to_status="in_progress",
        )

        if result.get("claimed"):
            console.print(f"[green]Claimed:[/green] {row['title']}")
            console.print(f"  Assignee: [cyan]{assignee}[/cyan]")
            console.print("  Status: [yellow]in_progress[/yellow]")
        else:
            console.print(f"[red]Failed:[/red] {result.get('error', 'Unknown error')}")
            raise typer.Exit(1)
    finally:
        db.close()


@sw_app.command("submit")
def sw_submit(
    item_id: str = typer.Argument(..., help="Backlog item ID"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
):
    """Submit an in-progress item for review."""
    from pyrite.services.kb_service import KBService

    from .workflows import BACKLOG_WORKFLOW, can_transition

    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "backlog_item", kb_name)
        match = [r for r in rows if r["id"] == item_id]
        if not match:
            console.print(f"[red]Error:[/red] Backlog item '{item_id}' not found.")
            raise typer.Exit(1)

        row = match[0]
        current_status = row.get("status") or row["_meta"].get("status", "proposed")
        item_kb = row.get("kb_name", kb_name or "")

        if not can_transition(BACKLOG_WORKFLOW, current_status, "review", "write"):
            console.print(
                f"[red]Error:[/red] Cannot transition from '{current_status}' to 'review'. "
                f"Item must be 'in_progress'."
            )
            raise typer.Exit(1)

        assignee = row.get("assignee") or row["_meta"].get("assignee", "")
        svc = KBService(config, db)
        result = svc.claim_entry(
            item_id,
            item_kb,
            assignee,
            from_status=current_status,
            to_status="review",
        )

        if result.get("claimed"):
            console.print(f"[green]Submitted for review:[/green] {row['title']}")
            console.print("  Status: [yellow]review[/yellow]")
        else:
            console.print(f"[red]Failed:[/red] {result.get('error', 'Unknown error')}")
            raise typer.Exit(1)
    finally:
        db.close()


@sw_app.command("transition")
def sw_transition(
    item_id: str = typer.Argument(..., help="Backlog item ID"),
    to_status: str = typer.Argument(..., help="Target status"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    reason: str | None = typer.Option(
        None, "--reason", "-r", help="Reason (required for some transitions)"
    ),
):
    """Transition a backlog item to a new status (validates workflow rules)."""
    from pyrite.services.kb_service import KBService

    from .workflows import (
        BACKLOG_WORKFLOW,
        can_transition,
        get_allowed_transitions,
        requires_reason,
    )

    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        rows = _query_entries(db, "backlog_item", kb_name)
        match = [r for r in rows if r["id"] == item_id]
        if not match:
            console.print(f"[red]Error:[/red] Backlog item '{item_id}' not found.")
            raise typer.Exit(1)

        row = match[0]
        current_status = row.get("status") or row["_meta"].get("status", "proposed")
        item_kb = row.get("kb_name", kb_name or "")

        if not can_transition(BACKLOG_WORKFLOW, current_status, to_status, "write"):
            allowed = get_allowed_transitions(BACKLOG_WORKFLOW, current_status, "write")
            targets = [t["to"] for t in allowed]
            console.print(
                f"[red]Error:[/red] Cannot transition from '{current_status}' to '{to_status}'. "
                f"Allowed: {', '.join(targets) or 'none'}"
            )
            raise typer.Exit(1)

        if requires_reason(BACKLOG_WORKFLOW, current_status, to_status) and not reason:
            console.print(
                f"[red]Error:[/red] Reason is required for transition from '{current_status}' to '{to_status}'. "
                f"Use --reason."
            )
            raise typer.Exit(1)

        assignee = row.get("assignee") or row["_meta"].get("assignee", "")
        svc = KBService(config, db)
        result = svc.claim_entry(
            item_id,
            item_kb,
            assignee,
            from_status=current_status,
            to_status=to_status,
        )

        if result.get("claimed"):
            console.print(f"[green]Transitioned:[/green] {row['title']}")
            console.print(f"  {current_status} -> [yellow]{to_status}[/yellow]")
            if reason:
                console.print(f"  Reason: {reason}")
        else:
            console.print(f"[red]Failed:[/red] {result.get('error', 'Unknown error')}")
            raise typer.Exit(1)
    finally:
        db.close()


@sw_app.command("pull-next")
def sw_pull_next(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """Recommend the next work item based on priority and WIP limits."""
    from .plugin import SoftwareKBPlugin

    plugin = SoftwareKBPlugin()
    result = plugin._mcp_pull_next({"kb_name": kb_name})

    if fmt == "json":
        _json_output(result)
        return

    rec = result.get("recommendation")
    if not rec:
        console.print(f"[dim]{result.get('reason', 'No items available')}[/dim]")
        return

    table = Table(title="Recommended Next Item")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("ID", rec["id"])
    table.add_row("Title", rec["title"])
    table.add_row("Kind", rec.get("kind", ""))
    table.add_row("Priority", rec.get("priority", ""))
    table.add_row("Effort", rec.get("effort", ""))

    wip = result.get("wip_status", {})
    if wip:
        limit_str = str(wip.get("limit", "-"))
        table.add_row("WIP", f"{wip.get('current', 0)}/{limit_str}")

    console.print(table)


@sw_app.command("review")
def sw_review_cmd(
    item_id: str = typer.Argument(..., help="Backlog item ID"),
    outcome: str = typer.Option(
        ..., "--outcome", "-o", help="Review outcome: approved or changes_requested"
    ),
    reviewer: str = typer.Option(..., "--reviewer", help="Who is reviewing"),
    feedback: str | None = typer.Option(None, "--feedback", help="Review notes/feedback"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
):
    """Record a review outcome for an item in review status."""
    from .plugin import SoftwareKBPlugin

    plugin = SoftwareKBPlugin()
    result = plugin._mcp_review(
        {
            "item_id": item_id,
            "kb_name": kb_name or "",
            "outcome": outcome,
            "reviewer": reviewer,
            "feedback": feedback,
        }
    )

    if result.get("reviewed"):
        console.print(f"[green]Reviewed:[/green] {item_id}")
        console.print(f"  Outcome: [yellow]{outcome}[/yellow]")
        console.print(f"  New status: [yellow]{result.get('new_status', '')}[/yellow]")
    else:
        console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")
        raise typer.Exit(1)


@sw_app.command("log")
def sw_log_cmd(
    item_id: str = typer.Argument(..., help="Backlog item ID"),
    summary: str = typer.Option(..., "--summary", "-s", help="Session summary"),
    decisions: str | None = typer.Option(None, "--decisions", help="Design choices made"),
    rejected: str | None = typer.Option(None, "--rejected", help="Approaches tried and abandoned"),
    open_questions: str | None = typer.Option(None, "--open-questions", help="Unresolved issues"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
):
    """Log a work session for a backlog item."""
    from .plugin import SoftwareKBPlugin

    plugin = SoftwareKBPlugin()
    result = plugin._mcp_log(
        {
            "item_id": item_id,
            "kb_name": kb_name or "",
            "summary": summary,
            "decisions": decisions or "",
            "rejected": rejected or "",
            "open_questions": open_questions or "",
        }
    )

    if result.get("created"):
        console.print(f"[green]Logged:[/green] {result['id']}")
        console.print(f"  Item: {item_id}")
        console.print(f"  Date: {result.get('date', '')}")
        console.print(f"  File: [cyan]{result.get('filename', '')}[/cyan]")
    else:
        console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")
        raise typer.Exit(1)


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
            _json_output(
                [
                    {
                        "title": r["title"],
                        "kind": r["_meta"].get("kind", ""),
                        "path": r["_meta"].get("path", ""),
                        "owner": r["_meta"].get("owner", ""),
                    }
                    for r in rows
                ]
            )
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


@sw_app.command("check-ready")
def sw_check_ready(
    item_id: str = typer.Argument(..., help="Backlog item ID"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """Check Definition of Ready for a backlog item without claiming it."""
    from .plugin import SoftwareKBPlugin

    plugin = SoftwareKBPlugin()
    result = plugin._mcp_check_ready({"item_id": item_id, "kb_name": kb_name or ""})

    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)

    if fmt == "json":
        _json_output(result)
        return

    ready_str = "[green]Ready[/green]" if result["ready"] else "[red]Not Ready[/red]"
    console.print(f"{ready_str}  [cyan]{result['item_id']}[/cyan]  {result['title']}")

    gate = result.get("gate")
    if gate and gate.get("criteria"):
        for c in gate["criteria"]:
            if c["passed"]:
                if c["type"] in ("judgment", "agent_responsibility"):
                    console.print(f"  [dim]⚑[/dim] {c['text']} [dim]({c['type']})[/dim]")
                else:
                    console.print(f"  [green]✓[/green] {c['text']}")
            else:
                msg = c.get("message", "")
                console.print(f"  [red]✗[/red] {c['text']}" + (f" — {msg}" if msg else ""))


@sw_app.command("refine")
def sw_refine_cmd(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB name"),
    status: str | None = typer.Option(None, "--status", "-s", help="Filter: proposed or accepted"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """Scan backlog for DoR gaps, sorted by priority."""
    from .plugin import SoftwareKBPlugin

    plugin = SoftwareKBPlugin()
    args: dict = {"kb_name": kb_name or ""}
    if status:
        args["status"] = status
    result = plugin._mcp_refine(args)

    if fmt == "json":
        _json_output(result)
        return

    summary = result.get("summary", {})
    not_ready = summary.get("not_ready", 0)
    ready = summary.get("ready", 0)

    if not_ready == 0 and ready == 0:
        console.print("[dim]No proposed/accepted items found.[/dim]")
        return

    if not_ready > 0:
        console.print(
            f"[bold]DoR Gaps[/bold] ({not_ready} with issues, {ready} ready)\n"
        )
    else:
        console.print(f"[bold green]All {ready} items ready to claim[/bold green]\n")

    for item in result.get("items", []):
        if item["ready"]:
            continue
        priority = item.get("priority", "medium")
        console.print(
            f"  [yellow]\\[{priority}][/yellow] [cyan]{item['id']}[/cyan]  {item['title']}"
        )
        gate = item.get("gate")
        if gate and gate.get("criteria"):
            for c in gate["criteria"]:
                if c["passed"]:
                    if c["type"] in ("judgment", "agent_responsibility"):
                        console.print(
                            f"    [dim]⚑[/dim] {c['text']} [dim]({c['type']})[/dim]"
                        )
                else:
                    msg = c.get("message", "")
                    console.print(
                        f"    [red]✗[/red] {c['text']}" + (f" — {msg}" if msg else "")
                    )

    if ready > 0:
        console.print(f"\n  [green]✓[/green] {ready} item{'s' if ready != 1 else ''} ready to claim")


@sw_app.command("context-for-item")
def sw_context_for_item(
    item_id: str = typer.Argument(..., help="Backlog item ID"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="KB name"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """Assemble full context bundle for a backlog item: linked ADRs, components, validations, conventions, reviews, work logs, dependencies."""
    from .plugin import SoftwareKBPlugin

    plugin = SoftwareKBPlugin()
    result = plugin._mcp_context_for_item({"item_id": item_id, "kb_name": kb_name})

    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)

    if fmt == "json":
        print(json.dumps(result, separators=(",", ":"), default=str))
        return

    # Rich output
    item = result.get("item", {})
    console.print(f"\n[bold]{item.get('title', '')}[/bold]")
    console.print(f"  ID: [cyan]{item.get('id', '')}[/cyan]")
    console.print(f"  Status: [yellow]{item.get('status', '')}[/yellow]")
    console.print(f"  Kind: {item.get('kind', '')}")
    console.print(f"  Priority: [red]{item.get('priority', '')}[/red]")

    if item.get("body"):
        console.print(f"\n[dim]{item['body'][:500]}[/dim]")

    # Dependencies
    deps = result.get("dependencies", {})
    if deps.get("is_blocked"):
        console.print("\n[red bold]BLOCKED[/red bold]")
    if deps.get("blocked_by"):
        console.print("\n[bold]Blocked By:[/bold]")
        for d in deps["blocked_by"]:
            status_style = "[green]" if d.get("status") == "done" else "[red]"
            console.print(f"  {status_style}{d.get('status', '')!s}[/] {d.get('id', '')} — {d.get('title', '')}")
    if deps.get("blocks"):
        console.print("\n[bold]Blocks:[/bold]")
        for d in deps["blocks"]:
            console.print(f"  [cyan]{d.get('id', '')}[/cyan] — {d.get('title', '')}")

    # Linked context sections
    _section_labels = [
        ("adrs", "Linked ADRs"),
        ("components", "Linked Components"),
        ("validations", "Validations"),
        ("conventions", "Conventions"),
        ("milestones", "Milestones"),
        ("work_logs", "Work Logs"),
        ("related", "Related"),
    ]
    for key, label in _section_labels:
        items = result.get(key, [])
        if items:
            console.print(f"\n[bold]{label}:[/bold]")
            for entry in items:
                relation = f" ({entry['relation']})" if entry.get("relation") else ""
                console.print(f"  [cyan]{entry.get('id', '')}[/cyan] {entry.get('title', '')}{relation}")
                if entry.get("body_preview"):
                    console.print(f"    [dim]{entry['body_preview']}[/dim]")

    # Reviews
    reviews = result.get("reviews", [])
    if reviews:
        console.print("\n[bold]Reviews:[/bold]")
        for r in reviews:
            result_style = "[green]" if r.get("result") == "approved" else "[yellow]"
            console.print(
                f"  {result_style}{r.get('result', '')}[/] by {r.get('reviewer', '')} "
                f"[dim]{r.get('created_at', '')}[/dim]"
            )
            if r.get("details"):
                console.print(f"    {r['details']}")
