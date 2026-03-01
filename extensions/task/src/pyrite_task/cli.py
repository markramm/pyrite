"""Task CLI commands."""

import json
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from pyrite.config import load_config
from pyrite.storage.database import PyriteDB

from .service import TaskService

task_app = typer.Typer(help="Task management commands")
console = Console()


def _format_output(data: dict, fmt: str) -> str | None:
    """Format data using the format registry. Returns None for default (rich) output."""
    if fmt == "rich":
        return None
    from pyrite.formats import format_response

    content, _ = format_response(data, fmt)
    return content


def _get_service() -> tuple[TaskService, PyriteDB]:
    """Create TaskService and return (service, db) for cleanup."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    return TaskService(config, db), db


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
    body: str | None = typer.Option(None, "--body", "-b", help="Task description"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """Create a new task."""
    svc, db = _get_service()
    try:
        result = svc.create_task(
            kb_name=kb_name,
            title=title,
            body=body or "",
            parent_task=parent or "",
            priority=priority,
            assignee=assignee or "",
        )

        formatted = _format_output(result, fmt)
        if formatted is not None:
            typer.echo(formatted)
            return

        console.print(f"[green]Task created:[/green] {result['title']}")
        console.print(f"  ID: [cyan]{result['entry_id']}[/cyan]")
        console.print(f"  Status: open, Priority: {priority}")
        if parent:
            console.print(f"  Parent: {parent}")
        if assignee:
            console.print(f"  Assignee: {assignee}")
    finally:
        db.close()


@task_app.command("list")
def task_list(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="Knowledge base name"),
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    assignee: str | None = typer.Option(None, "--assignee", "-a", help="Filter by assignee"),
    parent: str | None = typer.Option(None, "--parent", "-p", help="Filter by parent task"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """List tasks with optional filters."""
    svc, db = _get_service()
    try:
        items = svc.list_tasks(
            kb_name=kb_name,
            status=status,
            assignee=assignee,
            parent=parent,
        )

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
    svc, db = _get_service()
    try:
        task = svc.get_task(task_id, kb_name)
        if not task:
            console.print(f"[red]Error:[/red] Task '{task_id}' not found")
            raise typer.Exit(1)

        meta = task.get("metadata", {})
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                meta = {}

        children_list = svc.list_tasks(kb_name=kb_name, parent=task_id)
        children = [
            {"id": c["id"], "title": c["title"], "status": c["status"]}
            for c in children_list
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
            "kb_name": task.get("kb_name", kb_name or ""),
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
    updates: dict[str, Any] = {}
    if status is not None:
        updates["status"] = status
    if assignee is not None:
        updates["assignee"] = assignee
    if priority is not None:
        updates["priority"] = priority

    if not updates:
        console.print("[yellow]No updates specified.[/yellow]")
        raise typer.Exit(1)

    svc, db = _get_service()
    try:
        result = svc.update_task(task_id, kb_name, **updates)

        formatted = _format_output(result, fmt)
        if formatted is not None:
            typer.echo(formatted)
            return

        console.print(f"[green]Updated task:[/green] {task_id}")
        for k, v in updates.items():
            console.print(f"  {k}: {v}")
    finally:
        db.close()


@task_app.command("claim")
def task_claim(
    task_id: str = typer.Argument(..., help="Task entry ID"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    assignee: str = typer.Option(..., "--assignee", "-a", help="Assignee (e.g. agent:claude-code-7a3f)"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """Atomically claim an open task."""
    svc, db = _get_service()
    try:
        result = svc.claim_task(task_id, kb_name, assignee)

        formatted = _format_output(result, fmt)
        if formatted is not None:
            typer.echo(formatted)
            return

        if result.get("claimed"):
            console.print(f"[green]Claimed:[/green] {task_id}")
            console.print(f"  Assignee: {assignee}")
        else:
            console.print(f"[red]Failed:[/red] {result.get('error', 'Unknown error')}")
            raise typer.Exit(1)
    finally:
        db.close()


@task_app.command("decompose")
def task_decompose(
    parent_id: str = typer.Argument(..., help="Parent task entry ID"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    child: list[str] = typer.Option(..., "--child", "-c", help="Child task title (repeatable)"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """Decompose a parent task into child tasks."""
    children = [{"title": t} for t in child]
    svc, db = _get_service()
    try:
        results = svc.decompose_task(parent_id, kb_name, children)

        output = {"decomposed": True, "parent_id": parent_id, "children": results}
        formatted = _format_output(output, fmt)
        if formatted is not None:
            typer.echo(formatted)
            return

        console.print(f"[green]Decomposed:[/green] {parent_id}")
        for r in results:
            if r.get("created"):
                console.print(f"  [green]+[/green] {r['entry_id']}")
            else:
                console.print(f"  [red]x[/red] {r.get('error', 'Unknown error')}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        db.close()


@task_app.command("checkpoint")
def task_checkpoint(
    task_id: str = typer.Argument(..., help="Task entry ID"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    message: str = typer.Option(..., "--message", "-m", help="Checkpoint message"),
    confidence: float = typer.Option(0.0, "--confidence", help="Confidence 0.0-1.0"),
    evidence: list[str] | None = typer.Option(None, "--evidence", "-e", help="Evidence entry IDs (repeatable)"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json"),
):
    """Log a checkpoint on a task."""
    svc, db = _get_service()
    try:
        result = svc.checkpoint_task(
            task_id=task_id,
            kb_name=kb_name,
            message=message,
            confidence=confidence,
            partial_evidence=evidence,
        )

        formatted = _format_output(result, fmt)
        if formatted is not None:
            typer.echo(formatted)
            return

        console.print(f"[green]Checkpoint logged:[/green] {task_id}")
        console.print(f"  {message}")
        if confidence > 0:
            console.print(f"  Confidence: {int(confidence * 100)}%")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        db.close()
