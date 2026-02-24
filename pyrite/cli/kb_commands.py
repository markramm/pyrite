"""
KB management commands for pyrite CLI.

Commands: list, add, remove, discover, validate
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..config import (
    KBConfig,
    auto_discover_kbs,
    load_config,
    save_config,
)

kb_app = typer.Typer(help="Knowledge base management")
console = Console()


@kb_app.command("list")
def kb_list(
    kb_type: str | None = typer.Option(
        None, "--type", "-t", help="Filter by type (events/research)"
    ),
):
    """List all configured knowledge bases."""
    config = load_config()

    type_filter = kb_type
    kbs = config.list_kbs(type_filter)

    if not kbs:
        console.print("[yellow]No knowledge bases configured.[/yellow]")
        console.print("Add a KB with: pyrite kb add <path> --name <name>")
        return

    table = Table(title="Knowledge Bases")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Path")
    table.add_column("Status")

    for kb in kbs:
        errors = kb.validate()
        status = "[green]OK[/green]" if not errors else f"[red]{len(errors)} errors[/red]"
        table.add_row(kb.name, kb.kb_type, str(kb.path), status)

    console.print(table)


@kb_app.command("add")
def kb_add(
    path: Path = typer.Argument(..., help="Path to the knowledge base"),
    name: str | None = typer.Option(None, "--name", "-n", help="Name for the KB"),
    kb_type: str = typer.Option("research", "--type", "-t", help="KB type (events/research)"),
    description: str = typer.Option("", "--desc", "-d", help="Description"),
):
    """Add a knowledge base to the registry."""
    config = load_config()

    path = path.expanduser().resolve()
    if not path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {path}")
        raise typer.Exit(1)

    kb_name = name or path.name

    if config.get_kb(kb_name):
        console.print(f"[red]Error:[/red] KB with name '{kb_name}' already exists")
        raise typer.Exit(1)

    kb = KBConfig(name=kb_name, path=path, kb_type=kb_type, description=description)
    kb.load_kb_yaml()

    config.add_kb(kb)
    save_config(config)

    console.print(f"[green]Added KB:[/green] {kb_name} ({kb_type}) at {path}")


@kb_app.command("remove")
def kb_remove(
    name: str = typer.Argument(..., help="Name of the KB to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove a knowledge base from the registry."""
    config = load_config()

    kb = config.get_kb(name)
    if not kb:
        console.print(f"[red]Error:[/red] KB '{name}' not found")
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Remove KB '{name}' from registry?")
        if not confirm:
            raise typer.Abort()

    config.remove_kb(name)
    save_config(config)

    console.print(f"[green]Removed:[/green] {name}")
    console.print(f"[dim]Note: Files at {kb.path} were not deleted.[/dim]")


@kb_app.command("discover")
def kb_discover(
    search_path: Path | None = typer.Argument(None, help="Path to search for KBs"),
    add: bool = typer.Option(False, "--add", "-a", help="Add discovered KBs to registry"),
):
    """Auto-discover knowledge bases by finding kb.yaml files."""
    config = load_config()

    search_paths = [search_path] if search_path else [Path.cwd()]
    discovered = auto_discover_kbs(search_paths)

    if not discovered:
        console.print("[yellow]No KB configurations found.[/yellow]")
        return

    table = Table(title="Discovered Knowledge Bases")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Path")
    table.add_column("Status")

    for kb in discovered:
        existing = config.get_kb(kb.name)
        if existing:
            status = "[yellow]Already registered[/yellow]"
        else:
            status = "[green]New[/green]"
        table.add_row(kb.name, kb.kb_type, str(kb.path), status)

    console.print(table)

    if add:
        added = 0
        for kb in discovered:
            if not config.get_kb(kb.name):
                config.add_kb(kb)
                added += 1
        if added:
            save_config(config)
            console.print(f"[green]Added {added} KB(s) to registry.[/green]")


@kb_app.command("validate")
def kb_validate(
    name: str | None = typer.Argument(None, help="Name of KB to validate (all if omitted)"),
):
    """Validate knowledge base configuration and contents."""
    config = load_config()

    if name:
        kb = config.get_kb(name)
        if not kb:
            console.print(f"[red]Error:[/red] KB '{name}' not found")
            raise typer.Exit(1)
        kbs = [kb]
    else:
        kbs = config.knowledge_bases

    all_valid = True
    for kb in kbs:
        console.print(f"\n[bold]Validating {kb.name}...[/bold]")
        errors = kb.validate()
        if errors:
            all_valid = False
            for error in errors:
                console.print(f"  [red]✗[/red] {error}")
        else:
            console.print("  [green]✓[/green] Configuration valid")

            # Count entries
            if kb.path.exists():
                count = sum(
                    1 for f in kb.path.rglob("*.md") if not any(p.startswith(".") for p in f.parts)
                )
                console.print(f"  [green]✓[/green] {count} markdown files found")

    if all_valid:
        console.print("\n[green]All KBs valid.[/green]")
    else:
        console.print("\n[red]Validation errors found.[/red]")
        raise typer.Exit(1)


@kb_app.command("create")
def kb_create(
    name: str = typer.Option(..., "--name", "-n", help="Name for the KB"),
    path: Path | None = typer.Option(None, "--path", "-p", help="Path (auto for ephemeral)"),
    kb_type: str = typer.Option("generic", "--type", "-t", help="KB type"),
    description: str = typer.Option("", "--desc", "-d", help="Description"),
    shortname: str | None = typer.Option(
        None, "--shortname", "-s", help="Short alias for cross-KB links"
    ),
    ephemeral: bool = typer.Option(False, "--ephemeral", help="Create as ephemeral KB"),
    ttl: int = typer.Option(3600, "--ttl", help="TTL in seconds for ephemeral KBs"),
):
    """Create a new knowledge base."""
    from ..services.kb_service import KBService
    from ..storage.database import PyriteDB

    config = load_config()
    db = PyriteDB(config.settings.index_path)
    svc = KBService(config, db)

    if ephemeral:
        kb = svc.create_ephemeral_kb(name, ttl=ttl, description=description)
        console.print(f"[green]Created ephemeral KB:[/green] {name} (TTL: {ttl}s) at {kb.path}")
        return

    if not path:
        console.print("[red]Error:[/red] --path is required for non-ephemeral KBs")
        raise typer.Exit(1)

    resolved_path = path.expanduser().resolve()
    resolved_path.mkdir(parents=True, exist_ok=True)

    kb = KBConfig(
        name=name,
        path=resolved_path,
        kb_type=kb_type,
        description=description,
        shortname=shortname,
    )
    config.add_kb(kb)
    save_config(config)
    db.register_kb(name=name, kb_type=kb_type, path=str(resolved_path), description=description)
    console.print(f"[green]Created KB:[/green] {name} at {resolved_path}")


@kb_app.command("commit")
def kb_commit(
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    message: str = typer.Option(..., "--message", "-m", help="Commit message"),
    paths: list[str] | None = typer.Option(None, "--path", "-p", help="Specific file paths to commit"),
    sign_off: bool = typer.Option(False, "--signoff", "-s", help="Add Signed-off-by line"),
):
    """Commit changes in a KB's git repository."""
    from ..services.kb_service import KBService
    from ..storage.database import PyriteDB

    config = load_config()
    db = PyriteDB(config.settings.index_path)
    svc = KBService(config, db)

    try:
        result = svc.commit_kb(kb_name, message=message, paths=paths, sign_off=sign_off)
        if result["success"]:
            console.print(f"[green]Committed:[/green] {result['commit_hash'][:8]}")
            console.print(f"  {result['files_changed']} file(s) changed")
            if result.get("files"):
                for f in result["files"]:
                    console.print(f"  [dim]{f}[/dim]")
        else:
            console.print(f"[yellow]No commit:[/yellow] {result.get('error', 'Unknown error')}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        db.close()


@kb_app.command("push")
def kb_push(
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    remote: str = typer.Option("origin", "--remote", "-r", help="Remote name"),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Branch to push"),
):
    """Push KB commits to a remote repository."""
    from ..services.kb_service import KBService
    from ..storage.database import PyriteDB

    config = load_config()
    db = PyriteDB(config.settings.index_path)
    svc = KBService(config, db)

    try:
        result = svc.push_kb(kb_name, remote=remote, branch=branch)
        if result["success"]:
            console.print(f"[green]Pushed:[/green] {result['message']}")
        else:
            console.print(f"[red]Push failed:[/red] {result['message']}")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        db.close()


@kb_app.command("gc")
def kb_gc():
    """Garbage-collect expired ephemeral KBs."""
    from ..services.kb_service import KBService
    from ..storage.database import PyriteDB

    config = load_config()
    db = PyriteDB(config.settings.index_path)
    svc = KBService(config, db)
    removed = svc.gc_ephemeral_kbs()

    if removed:
        for name in removed:
            console.print(f"  [red]Removed:[/red] {name}")
        console.print(f"[green]Garbage collected {len(removed)} expired KB(s).[/green]")
    else:
        console.print("[dim]No expired ephemeral KBs found.[/dim]")
