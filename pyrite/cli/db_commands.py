"""
Database backup and restore commands for pyrite CLI.

Commands: backup, restore
"""

import logging
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from ..config import load_config

logger = logging.getLogger(__name__)

db_app = typer.Typer(help="Database backup and restore.")
console = Console()


@db_app.command("backup")
def db_backup(
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output path for the backup file"),
    ] = None,
):
    """Create a backup of the Pyrite index database."""
    config = load_config()
    db_path = config.settings.index_path

    if not db_path.exists():
        console.print("[red]Error:[/red] Database file does not exist.")
        raise typer.Exit(1)

    if output is None:
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        output = f"pyrite-backup-{timestamp}.db"

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use SQLite's backup API for safe, consistent backups
    source_conn = sqlite3.connect(str(db_path))
    dest_conn = sqlite3.connect(str(output_path))
    try:
        source_conn.backup(dest_conn)
    finally:
        dest_conn.close()
        source_conn.close()

    console.print(f"Backup created: {output_path}")


@db_app.command("restore")
def db_restore(
    backup_path: Annotated[str, typer.Argument(help="Path to backup file to restore from")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
):
    """Restore the Pyrite index database from a backup."""
    backup = Path(backup_path)

    if not backup.exists():
        console.print(f"[red]Error:[/red] Backup file not found: {backup}")
        raise typer.Exit(1)

    # Validate it's a real SQLite database
    try:
        conn = sqlite3.connect(str(backup))
        conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        conn.close()
    except sqlite3.DatabaseError:
        console.print(f"[red]Error:[/red] Not a valid SQLite database: {backup}")
        raise typer.Exit(1)

    if not force:
        console.print(
            "[yellow]Warning:[/yellow] This will overwrite the current database. "
            "Use --force to confirm."
        )
        raise typer.Exit(1)

    config = load_config()
    db_path = config.settings.index_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy the backup over the current database
    shutil.copy2(str(backup), str(db_path))

    console.print(f"Restored database from {backup}")
