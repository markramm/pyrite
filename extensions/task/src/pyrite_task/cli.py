"""Task CLI commands."""

import json

import typer
from rich.console import Console
from rich.table import Table

from pyrite.config import load_config
from pyrite.storage.database import PyriteDB

task_app = typer.Typer(help="Task management commands")
console = Console()


def _format_output(data: dict, fmt: str) -> str | None:
    """Format data using the format registry. Returns None for default (rich) output."""
    if fmt == "rich":
        return None
    from pyrite.formats import format_response

    content, _ = format_response(data, fmt)
    return content


def _query_tasks(db: PyriteDB, kb_name: str | None = None) -> list[dict]:
    """Query task entries with parsed metadata."""
    query = "SELECT * FROM entry WHERE entry_type = ?"
    params: list = ["task"]
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


@task_app.command("create")
def task_create(
    title: str = typer.Argument(..., help="Task title"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    parent: str | None = typer.Option(None, "--parent", "-p", help="Parent task entry ID"),
    priority: int = typer.Option(5, "--priority", help="Priority 1-10"),
    assignee: str | None = typer.Option(None, "--assignee", "-a", help="Assignee (e.g. agent:claude-code-7a3f)"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """Create a new task."""
    slug = title.lower().replace(" ", "-")
    result = {
        "created": True,
        "title": title,
        "status": "open",
        "priority": priority,
        "filename": f"tasks/{slug}.md",
    }
    if parent:
        result["parent_task"] = parent
    if assignee:
        result["assignee"] = assignee

    formatted = _format_output(result, fmt)
    if formatted is not None:
        typer.echo(formatted)
        return

    console.print(f"[green]Task created:[/green] {title}")
    console.print(f"  File: {result['filename']}")
    console.print(f"  Status: open, Priority: {priority}")
    if parent:
        console.print(f"  Parent: {parent}")
    if assignee:
        console.print(f"  Assignee: {assignee}")


@task_app.command("list")
def task_list(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="Knowledge base name"),
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    assignee: str | None = typer.Option(None, "--assignee", "-a", help="Filter by assignee"),
    parent: str | None = typer.Option(None, "--parent", "-p", help="Filter by parent task"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """List tasks with optional filters."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    try:
        rows = _query_tasks(db, kb_name)
        if status:
            rows = [r for r in rows if r["_meta"].get("status", "open") == status]
        if assignee:
            rows = [r for r in rows if r["_meta"].get("assignee", "") == assignee]
        if parent:
            rows = [r for r in rows if r["_meta"].get("parent_task", "") == parent]

        items = [
            {
                "id": r["id"],
                "title": r["title"],
                "status": r["_meta"].get("status", "open"),
                "assignee": r["_meta"].get("assignee", ""),
                "priority": r["_meta"].get("priority", 5),
                "parent_task": r["_meta"].get("parent_task", ""),
                "kb_name": r["kb_name"],
            }
            for r in rows
        ]

        formatted = _format_output({"count": len(items), "tasks": items}, fmt)
        if formatted is not None:
            typer.echo(formatted)
            return

        table = Table(title="Tasks")
        table.add_column("ID", style="cyan", max_width=12)
        table.add_column("Title")
        table.add_column("Status", style="green")
        table.add_column("Pri", justify="right")
        table.add_column("Assignee", style="yellow")
        table.add_column("Parent", style="dim", max_width=12)

        for item in items:
            table.add_row(
                item["id"][:12],
                item["title"],
                item["status"],
                str(item["priority"]),
                item["assignee"],
                item["parent_task"][:12] if item["parent_task"] else "",
            )
        console.print(table)
    finally:
        db.close()


@task_app.command("status")
def task_status(
    task_id: str = typer.Argument(..., help="Task entry ID"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="Knowledge base name"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """Show task details with children, dependencies, and evidence."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    try:
        rows = _query_tasks(db, kb_name)
        task = None
        for r in rows:
            if r["id"] == task_id:
                task = r
                break

        if not task:
            console.print(f"[red]Error:[/red] Task '{task_id}' not found")
            raise typer.Exit(1)

        meta = task["_meta"]
        children = [
            {"id": r["id"], "title": r["title"], "status": r["_meta"].get("status", "open")}
            for r in rows
            if r["_meta"].get("parent_task", "") == task_id
        ]

        result = {
            "id": task["id"],
            "title": task["title"],
            "status": meta.get("status", "open"),
            "assignee": meta.get("assignee", ""),
            "priority": meta.get("priority", 5),
            "parent_task": meta.get("parent_task", ""),
            "dependencies": meta.get("dependencies", []),
            "evidence": meta.get("evidence", []),
            "due_date": meta.get("due_date", ""),
            "agent_context": meta.get("agent_context", {}),
            "children": children,
            "kb_name": task["kb_name"],
        }

        formatted = _format_output(result, fmt)
        if formatted is not None:
            typer.echo(formatted)
            return

        console.print(f"\n[bold]{result['title']}[/bold]")
        console.print(f"  ID: [cyan]{result['id']}[/cyan]")
        console.print(f"  Status: [green]{result['status']}[/green]")
        console.print(f"  Priority: {result['priority']}")
        if result["assignee"]:
            console.print(f"  Assignee: [yellow]{result['assignee']}[/yellow]")
        if result["parent_task"]:
            console.print(f"  Parent: {result['parent_task']}")
        if result["due_date"]:
            console.print(f"  Due: {result['due_date']}")
        if result["dependencies"]:
            console.print(f"  Dependencies: {', '.join(result['dependencies'])}")
        if result["evidence"]:
            console.print(f"  Evidence: {', '.join(result['evidence'])}")
        if children:
            console.print(f"\n  [bold]Children ({len(children)}):[/bold]")
            for c in children:
                console.print(f"    {c['id'][:12]}  {c['status']:12}  {c['title']}")
    finally:
        db.close()


@task_app.command("update")
def task_update(
    task_id: str = typer.Argument(..., help="Task entry ID"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    status: str | None = typer.Option(None, "--status", "-s", help="New status"),
    assignee: str | None = typer.Option(None, "--assignee", "-a", help="New assignee"),
    priority: int | None = typer.Option(None, "--priority", help="New priority 1-10"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """Update task fields (status, assignee, priority)."""
    updates = {}
    if status is not None:
        updates["status"] = status
    if assignee is not None:
        updates["assignee"] = assignee
    if priority is not None:
        updates["priority"] = priority

    if not updates:
        console.print("[yellow]No updates specified.[/yellow]")
        raise typer.Exit(1)

    result = {"updated": True, "task_id": task_id, "updates": updates}

    formatted = _format_output(result, fmt)
    if formatted is not None:
        typer.echo(formatted)
        return

    console.print(f"[green]Updated task:[/green] {task_id}")
    for k, v in updates.items():
        console.print(f"  {k}: {v}")
