"""Schema versioning CLI commands."""

import json
import logging

import typer
from rich.console import Console
from rich.table import Table

from .context import cli_context

logger = logging.getLogger(__name__)
console = Console()

schema_app = typer.Typer(help="Schema versioning and migration commands")


@schema_app.command("diff")
def schema_diff(
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    entry_type: str = typer.Option(None, "--type", "-t", help="Filter by entry type"),
):
    """Show schema types with version and field annotations."""
    with cli_context() as (config, db, svc):
        kb_config = config.get_kb(kb_name)
        if not kb_config:
            console.print(f"[red]Error:[/red] KB '{kb_name}' not found")
            raise typer.Exit(1)

        if not kb_config.kb_yaml_path.exists():
            console.print(f"[yellow]No kb.yaml found for '{kb_name}'[/yellow]")
            raise typer.Exit(1)

        schema = kb_config.kb_schema
        console.print(f"[bold]Schema for KB '{kb_name}'[/bold]")
        console.print(f"[dim]Schema version: {schema.schema_version}[/dim]\n")

        types_to_show = {entry_type: schema.types[entry_type]} if entry_type and entry_type in schema.types else schema.types

        for type_name, type_schema in types_to_show.items():
            console.print(f"[bold cyan]{type_name}[/bold cyan] (v{type_schema.version})")
            if not type_schema.fields:
                console.print("  [dim]No typed fields defined[/dim]")
                continue

            table = Table(show_header=True, box=None, padding=(0, 2))
            table.add_column("Field", style="white")
            table.add_column("Type", style="dim")
            table.add_column("Required", style="dim")
            table.add_column("Since", style="yellow")

            for field_name, field_schema in type_schema.fields.items():
                since = str(field_schema.since_version) if field_schema.since_version is not None else ""
                req = "yes" if field_schema.required else ""
                table.add_row(field_name, field_schema.field_type, req, since)

            console.print(table)
            console.print()


@schema_app.command("migrate")
def schema_migrate(
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    entry_type: str = typer.Option(None, "--type", "-t", help="Filter by entry type"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be migrated without saving"),
):
    """Migrate entries to current schema version.

    Loads and re-saves all entries, applying any pending migrations.
    """
    from ..storage.repository import KBRepository

    with cli_context() as (config, db, svc):
        kb_config = config.get_kb(kb_name)
        if not kb_config:
            console.print(f"[red]Error:[/red] KB '{kb_name}' not found")
            raise typer.Exit(1)

        repo = KBRepository(kb_config)
        checked = 0
        migrated = 0
        errors = 0

        for file_path in repo.list_files():
            try:
                entry = repo._load_entry(file_path)
                if entry_type and entry.entry_type != entry_type:
                    continue

                checked += 1

                # Check if version changed (migration happened on load)
                type_schema = kb_config.kb_schema.get_type_schema(entry.entry_type)
                needs_save = (
                    type_schema
                    and type_schema.version > 0
                    and entry._schema_version != type_schema.version
                )

                if needs_save:
                    migrated += 1
                    if not dry_run:
                        entry._schema_version = type_schema.version
                        entry.kb_name = kb_name
                        entry.file_path = file_path
                        entry.save(file_path)
            except Exception as e:
                errors += 1
                logger.warning("Migration error for %s: %s", file_path, e)

        label = "[dim](dry run)[/dim] " if dry_run else ""
        console.print(f"\n{label}[bold]Migration results for '{kb_name}':[/bold]")
        console.print(f"  Checked: {checked}")
        console.print(f"  Migrated: {migrated}")
        if errors:
            console.print(f"  [red]Errors: {errors}[/red]")
        if migrated == 0:
            console.print("  [green]All entries are up to date.[/green]")
