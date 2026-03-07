"""
KB management commands for pyrite CLI.

Commands: list, add, remove, discover, validate, create, reindex, health, commit, push, gc
"""

from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from ..config import (
    auto_discover_kbs,
    load_config,
    save_config,
)
from .context import cli_context, cli_registry_context

kb_app = typer.Typer(help="Knowledge base management")
console = Console()


def _format_output(data: dict, fmt: str) -> str | None:
    """Format data using the format registry. Returns None for default (rich) output."""
    if fmt == "rich":
        return None
    from ..formats import format_response

    content, _ = format_response(data, fmt)
    return content


@kb_app.command("list")
def kb_list(
    kb_type: str | None = typer.Option(
        None, "--type", "-t", help="Filter by type (events/research)"
    ),
    output_format: str = typer.Option(
        "json", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
):
    """List all configured knowledge bases."""
    with cli_registry_context() as (config, db, svc, registry):
        kbs = registry.list_kbs(type_filter=kb_type)

        if not kbs:
            console.print("[yellow]No knowledge bases configured.[/yellow]")
            console.print("Add a KB with: pyrite kb add <path> --name <name>")
            return

        formatted = _format_output({"kbs": kbs}, output_format)
        if formatted is not None:
            typer.echo(formatted)
            return

        table = Table(title="Knowledge Bases")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Source", style="magenta")
        table.add_column("Entries", justify="right")
        table.add_column("Last Indexed")
        table.add_column("Path")

        for kb in kbs:
            table.add_row(
                kb["name"],
                kb["type"],
                kb.get("source", "user"),
                str(kb.get("entries", 0)),
                kb.get("last_indexed", "never") or "never",
                kb["path"],
            )

        console.print(table)


@kb_app.command("add")
def kb_add(
    path: Path = typer.Argument(..., help="Path to the knowledge base"),
    name: str | None = typer.Option(None, "--name", "-n", help="Name for the KB"),
    kb_type: str = typer.Option("generic", "--type", "-t", help="KB type"),
    description: str = typer.Option("", "--desc", "-d", help="Description"),
):
    """Add a knowledge base to the registry."""
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {resolved}")
        raise typer.Exit(1)

    kb_name = name or resolved.name

    with cli_registry_context() as (config, db, svc, registry):
        try:
            result = registry.add_kb(
                name=kb_name, path=str(resolved), kb_type=kb_type, description=description
            )
            console.print(f"[green]Added KB:[/green] {result['name']} ({result['type']}) at {result['path']}")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@kb_app.command("remove")
def kb_remove(
    name: str = typer.Argument(..., help="Name of the KB to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove a knowledge base from the registry."""
    with cli_registry_context() as (config, db, svc, registry):
        kb = registry.get_kb(name)
        if not kb:
            console.print(f"[red]Error:[/red] KB '{name}' not found")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Remove KB '{name}' from registry?")
            if not confirm:
                raise typer.Abort()

        from ..exceptions import KBProtectedError

        try:
            registry.remove_kb(name)
            console.print(f"[green]Removed:[/green] {name}")
            console.print(f"[dim]Note: Files at {kb['path']} were not deleted.[/dim]")
        except KBProtectedError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@kb_app.command("discover")
def kb_discover(
    search_path: Path | None = typer.Argument(None, help="Path to search for KBs"),
    add: bool = typer.Option(False, "--add", "-a", help="Add discovered KBs to registry"),
    output_format: str = typer.Option(
        "json", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
):
    """Auto-discover knowledge bases by finding kb.yaml files."""
    config = load_config()

    search_paths = [search_path] if search_path else [Path.cwd()]
    discovered = auto_discover_kbs(search_paths)

    if not discovered:
        console.print("[yellow]No KB configurations found.[/yellow]")
        return

    formatted = _format_output(
        {
            "discovered": [
                {
                    "name": kb.name,
                    "type": kb.kb_type,
                    "path": str(kb.path),
                    "already_registered": config.get_kb(kb.name) is not None,
                }
                for kb in discovered
            ]
        },
        output_format,
    )
    if formatted is not None:
        typer.echo(formatted)
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
    output_format: str = typer.Option(
        "json", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
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

    # Collect results for all KBs
    kb_results = []
    all_valid = True
    for kb in kbs:
        errors = kb.validate()
        if errors:
            all_valid = False
        kb_results.append({"name": kb.name, "valid": len(errors) == 0, "errors": errors})

    formatted = _format_output(
        {"kbs": kb_results, "all_valid": all_valid},
        output_format,
    )
    if formatted is not None:
        typer.echo(formatted)
        return

    # Rich output
    for kb_res in kb_results:
        console.print(f"\n[bold]Validating {kb_res['name']}...[/bold]")
        if kb_res["errors"]:
            for error in kb_res["errors"]:
                console.print(f"  [red]✗[/red] {error}")
        else:
            console.print("  [green]✓[/green] Configuration valid")

            # Count entries — find the matching KB config for path
            matching_kb = config.get_kb(kb_res["name"])
            if matching_kb and matching_kb.path.exists():
                count = sum(
                    1
                    for f in matching_kb.path.rglob("*.md")
                    if not any(p.startswith(".") for p in f.parts)
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
    with cli_registry_context() as (config, db, svc, registry):
        if ephemeral:
            kb = svc.create_ephemeral_kb(name, ttl=ttl, description=description)
            console.print(f"[green]Created ephemeral KB:[/green] {name} (TTL: {ttl}s) at {kb.path}")
            return

        if not path:
            console.print("[red]Error:[/red] --path is required for non-ephemeral KBs")
            raise typer.Exit(1)

        resolved_path = path.expanduser().resolve()
        resolved_path.mkdir(parents=True, exist_ok=True)

        try:
            registry.add_kb(
                name=name,
                path=str(resolved_path),
                kb_type=kb_type,
                description=description,
            )
            console.print(f"[green]Created KB:[/green] {name} at {resolved_path}")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@kb_app.command("reindex")
def kb_reindex(
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    output_format: str = typer.Option(
        "json", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
):
    """Reindex a specific knowledge base."""
    with cli_registry_context() as (config, db, svc, registry):
        from ..exceptions import KBNotFoundError

        try:
            result = registry.reindex_kb(kb_name)
        except KBNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        data = {"name": kb_name, **result}
        formatted = _format_output(data, output_format)
        if formatted is not None:
            typer.echo(formatted)
            return

        console.print(f"[green]Reindexed:[/green] {kb_name}")
        console.print(f"  Added: {result['added']}, Updated: {result['updated']}, Removed: {result['removed']}")


@kb_app.command("health")
def kb_health(
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    output_format: str = typer.Option(
        "json", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
):
    """Check health of a knowledge base."""
    with cli_registry_context() as (config, db, svc, registry):
        from ..exceptions import KBNotFoundError

        try:
            result = registry.health_kb(kb_name)
        except KBNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        formatted = _format_output(result, output_format)
        if formatted is not None:
            typer.echo(formatted)
            return

        status = "[green]Healthy[/green]" if result["healthy"] else "[red]Unhealthy[/red]"
        console.print(f"\n[bold]{kb_name}[/bold]: {status}")
        console.print(f"  Path: {result['path']} ({'exists' if result['path_exists'] else 'MISSING'})")
        console.print(f"  Files: {result['file_count']}, Indexed entries: {result['entry_count']}")
        console.print(f"  Last indexed: {result['last_indexed'] or 'never'}")
        console.print(f"  Source: {result['source']}")


@kb_app.command("commit")
def kb_commit(
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    message: str = typer.Option(..., "--message", "-m", help="Commit message"),
    paths: list[str] | None = typer.Option(
        None, "--path", "-p", help="Specific file paths to commit"
    ),
    sign_off: bool = typer.Option(False, "--signoff", "-s", help="Add Signed-off-by line"),
):
    """Commit changes in a KB's git repository."""
    with cli_context() as (config, db, svc):
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


@kb_app.command("push")
def kb_push(
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    remote: str = typer.Option("origin", "--remote", "-r", help="Remote name"),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Branch to push"),
):
    """Push KB commits to a remote repository."""
    with cli_context() as (config, db, svc):
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


@kb_app.command("gc")
def kb_gc():
    """Garbage-collect expired ephemeral KBs."""
    with cli_context() as (config, db, svc):
        removed = svc.gc_ephemeral_kbs()

        if removed:
            for name in removed:
                console.print(f"  [red]Removed:[/red] {name}")
            console.print(f"[green]Garbage collected {len(removed)} expired KB(s).[/green]")
        else:
            console.print("[dim]No expired ephemeral KBs found.[/dim]")


# =========================================================================
# Schema provisioning
# =========================================================================

schema_app = typer.Typer(help="Schema provisioning — manage kb.yaml types programmatically")
kb_app.add_typer(schema_app, name="schema")


@schema_app.command("show")
def schema_show(
    kb_name: str = typer.Argument(..., help="Knowledge base name"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """Show the current schema for a KB."""
    from ..services.schema_service import SchemaService

    config = load_config()
    try:
        svc = SchemaService(config)
        result = svc.show_schema(kb_name)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    formatted = _format_output(result, output_format)
    if formatted is not None:
        typer.echo(formatted)
        return

    console.print(f"\n[bold]Schema for {kb_name}[/bold]")
    types = result.get("types", {})
    if types:
        table = Table(title="Types")
        table.add_column("Type", style="cyan")
        table.add_column("Description")
        table.add_column("Required")
        table.add_column("Optional")
        table.add_column("Subdirectory")
        for name, tdef in types.items():
            table.add_row(
                name,
                tdef.get("description", ""),
                ", ".join(tdef.get("required", [])),
                ", ".join(tdef.get("optional", [])),
                tdef.get("subdirectory", ""),
            )
        console.print(table)
    else:
        console.print("  [dim]No types defined[/dim]")

    policies = result.get("policies", {})
    if policies:
        console.print(f"\n  [bold]Policies:[/bold] {policies}")
    validation = result.get("validation", {})
    if validation:
        console.print(f"  [bold]Validation:[/bold] {validation}")


@schema_app.command("add-type")
def schema_add_type(
    kb_name: str = typer.Argument(..., help="Knowledge base name"),
    type_name: str = typer.Option(..., "--type", "-t", help="Type name to add"),
    description: str = typer.Option("", "--description", "-d", help="Type description"),
    required: str = typer.Option("", "--required", "-r", help="Comma-separated required fields"),
    optional: str = typer.Option("", "--optional", "-o", help="Comma-separated optional fields"),
    subdirectory: str = typer.Option("", "--subdirectory", "-s", help="Subdirectory for files"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """Add a type definition to a KB's schema."""
    from ..services.schema_service import SchemaService

    config = load_config()
    type_def: dict[str, Any] = {}
    if description:
        type_def["description"] = description
    if required:
        type_def["required"] = [f.strip() for f in required.split(",") if f.strip()]
    if optional:
        type_def["optional"] = [f.strip() for f in optional.split(",") if f.strip()]
    if subdirectory:
        type_def["subdirectory"] = subdirectory

    try:
        svc = SchemaService(config)
        result = svc.add_type(kb_name, type_name, type_def)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)

    formatted = _format_output(result, output_format)
    if formatted is not None:
        typer.echo(formatted)
        return

    console.print(f"[green]Added type:[/green] {type_name} to {kb_name}")


@schema_app.command("remove-type")
def schema_remove_type(
    kb_name: str = typer.Argument(..., help="Knowledge base name"),
    type_name: str = typer.Option(..., "--type", "-t", help="Type name to remove"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """Remove a type definition from a KB's schema."""
    from ..services.schema_service import SchemaService

    config = load_config()
    try:
        svc = SchemaService(config)
        result = svc.remove_type(kb_name, type_name)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)

    formatted = _format_output(result, output_format)
    if formatted is not None:
        typer.echo(formatted)
        return

    console.print(f"[green]Removed type:[/green] {type_name} from {kb_name}")


@schema_app.command("set")
def schema_set(
    kb_name: str = typer.Argument(..., help="Knowledge base name"),
    schema_file: Path = typer.Option(..., "--schema-file", "-s", help="YAML file with schema"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json, rich"),
):
    """Replace schema from a YAML file."""
    from ..services.schema_service import SchemaService
    from ..utils.yaml import load_yaml_file as load_yaml

    config = load_config()

    if not schema_file.exists():
        console.print(f"[red]Error:[/red] File not found: {schema_file}")
        raise typer.Exit(1)

    schema = load_yaml(schema_file)

    try:
        svc = SchemaService(config)
        result = svc.set_schema(kb_name, schema)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    formatted = _format_output(result, output_format)
    if formatted is not None:
        typer.echo(formatted)
        return

    console.print(f"[green]Set schema:[/green] {result['type_count']} types in {kb_name}")
