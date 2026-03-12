"""CLI commands for the Cascade Series plugin."""

import json
from pathlib import Path
from typing import Optional

import typer

cascade_app = typer.Typer(help="Cascade Series commands")


@cascade_app.command("suggest-aliases")
def suggest_aliases(
    kb_name: str = typer.Option("cascade-timeline", "--kb", "-k", help="KB name"),
    min_confidence: int = typer.Option(
        90, "--min-confidence", "-c", help="Auto-accept threshold (0-100)"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write accepted aliases to JSON file"
    ),
    show_all: bool = typer.Option(
        False, "--all", "-a", help="Show all proposals, not just auto-accepted"
    ),
) -> None:
    """Detect duplicate actor names and suggest canonical aliases."""
    from pyrite.config import load_config
    from pyrite.storage.database import PyriteDB

    from .aliases import apply_proposals, extract_actor_counts_from_db, run_detection

    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        actor_counts = extract_actor_counts_from_db(db, kb_name)
        if not actor_counts:
            typer.echo("No actors found in events.")
            raise typer.Exit()

        typer.echo(f"Found {len(actor_counts)} unique actor names across {sum(actor_counts.values())} references.")
        proposals = run_detection(actor_counts)

        if not proposals:
            typer.echo("No duplicates detected.")
            raise typer.Exit()

        typer.echo(f"\nDetected {len(proposals)} duplicate group(s):\n")

        for p in proposals:
            marker = "✓" if p.confidence >= min_confidence else "○"
            typer.echo(f"  {marker} [{p.confidence}%] {p.canonical}")
            typer.echo(f"    strategy: {p.strategy}")
            typer.echo(f"    aliases: {', '.join(p.aliases)}")
            typer.echo()

        accepted = apply_proposals(proposals, min_confidence=min_confidence)
        typer.echo(f"Auto-accepted: {len(accepted)} group(s) (confidence >= {min_confidence}%)")

        if output and accepted:
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w") as f:
                json.dump(accepted, f, indent=2)
            typer.echo(f"Written to {output}")
    finally:
        db.close()
