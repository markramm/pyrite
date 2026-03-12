"""Journalism Investigation CLI commands."""

import json as json_mod

import typer
from rich.console import Console
from rich.table import Table

from pyrite.config import load_config
from pyrite.storage.database import PyriteDB

from .plugin import JournalismInvestigationPlugin, _parse_meta

investigation_app = typer.Typer(help="Journalism investigation commands")
console = Console()


def _get_plugin_with_db():
    """Create a plugin instance with DB context for CLI usage."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    plugin = JournalismInvestigationPlugin()
    # Set minimal context so _get_db() returns the injected DB
    from dataclasses import dataclass

    @dataclass
    class _CLIContext:
        db: PyriteDB
        config: object = None

    plugin.set_context(_CLIContext(db=db, config=config))
    return plugin, db


@investigation_app.command("timeline")
def timeline(
    kb_name: str = typer.Option(..., "--kb", "-k", help="KB name"),
    from_date: str = typer.Option("", "--from", help="Start date (YYYY-MM-DD)"),
    to_date: str = typer.Option("", "--to", help="End date (YYYY-MM-DD)"),
    actor: str = typer.Option("", "--actor", help="Filter by actor name"),
    event_type: str = typer.Option("", "--type", help="Filter by type: investigation_event, transaction, legal_action"),
    min_importance: int = typer.Option(0, "--min-importance", help="Minimum importance (1-10)"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Query investigation events by date range, actor, and type."""
    plugin, db = _get_plugin_with_db()
    try:
        args = {"kb_name": kb_name, "limit": limit}
        if from_date:
            args["from_date"] = from_date
        if to_date:
            args["to_date"] = to_date
        if actor:
            args["actor"] = actor
        if event_type:
            args["event_type"] = event_type
        if min_importance:
            args["min_importance"] = min_importance

        result = plugin._mcp_timeline(args)

        if output_json:
            console.print(json_mod.dumps(result, indent=2))
            return

        if not result["events"]:
            console.print("[dim]No events found.[/dim]")
            return

        table = Table(title=f"Timeline ({result['count']} events)")
        table.add_column("Date", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Title")
        table.add_column("Imp", justify="right")
        table.add_column("Actors", style="dim")

        for e in result["events"]:
            table.add_row(
                e.get("date", ""),
                e.get("type", ""),
                e.get("title", ""),
                str(e.get("importance", "")),
                ", ".join(e.get("actors", [])),
            )
        console.print(table)
    finally:
        db.close()


@investigation_app.command("entities")
def entities(
    kb_name: str = typer.Option(..., "--kb", "-k", help="KB name"),
    entity_type: str = typer.Option("", "--type", help="Filter by type: person, organization, asset, account"),
    jurisdiction: str = typer.Option("", "--jurisdiction", help="Filter by jurisdiction"),
    min_importance: int = typer.Option(0, "--min-importance", help="Minimum importance (1-10)"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Query investigation entities by type, importance, and jurisdiction."""
    plugin, db = _get_plugin_with_db()
    try:
        args = {"kb_name": kb_name, "limit": limit}
        if entity_type:
            args["entity_type"] = entity_type
        if jurisdiction:
            args["jurisdiction"] = jurisdiction
        if min_importance:
            args["min_importance"] = min_importance

        result = plugin._mcp_entities(args)

        if output_json:
            console.print(json_mod.dumps(result, indent=2))
            return

        if not result["entities"]:
            console.print("[dim]No entities found.[/dim]")
            return

        table = Table(title=f"Entities ({result['count']})")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Title")
        table.add_column("Imp", justify="right")

        for e in result["entities"]:
            table.add_row(e["id"], e["type"], e["title"], str(e["importance"]))
        console.print(table)
    finally:
        db.close()


@investigation_app.command("sources")
def sources(
    kb_name: str = typer.Option(..., "--kb", "-k", help="KB name"),
    reliability: str = typer.Option("", "--reliability", help="Filter: high, medium, low, unknown"),
    classification: str = typer.Option("", "--classification", help="Filter: public, leaked, foia, etc."),
    from_date: str = typer.Option("", "--from", help="Start date (YYYY-MM-DD)"),
    to_date: str = typer.Option("", "--to", help="End date (YYYY-MM-DD)"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Query source documents by reliability and classification."""
    plugin, db = _get_plugin_with_db()
    try:
        args = {"kb_name": kb_name, "limit": limit}
        if reliability:
            args["reliability"] = reliability
        if classification:
            args["classification"] = classification
        if from_date:
            args["from_date"] = from_date
        if to_date:
            args["to_date"] = to_date

        result = plugin._mcp_sources(args)

        if output_json:
            console.print(json_mod.dumps(result, indent=2))
            return

        if not result["sources"]:
            console.print("[dim]No sources found.[/dim]")
            return

        table = Table(title=f"Sources ({result['count']})")
        table.add_column("ID", style="cyan")
        table.add_column("Reliability", style="green")
        table.add_column("Classification")
        table.add_column("Title")
        table.add_column("Date", style="dim")

        for s in result["sources"]:
            table.add_row(s["id"], s["reliability"], s.get("classification", ""), s["title"], s.get("date", ""))
        console.print(table)
    finally:
        db.close()


@investigation_app.command("claims")
def claims(
    kb_name: str = typer.Option(..., "--kb", "-k", help="KB name"),
    status: str = typer.Option("", "--status", help="Filter: unverified, partially_verified, corroborated, disputed, retracted"),
    confidence: str = typer.Option("", "--confidence", help="Filter: high, medium, low"),
    min_importance: int = typer.Option(0, "--min-importance", help="Minimum importance (1-10)"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Query claims by status and confidence level."""
    plugin, db = _get_plugin_with_db()
    try:
        args = {"kb_name": kb_name, "limit": limit}
        if status:
            args["claim_status"] = status
        if confidence:
            args["confidence"] = confidence
        if min_importance:
            args["min_importance"] = min_importance

        result = plugin._mcp_claims(args)

        if output_json:
            console.print(json_mod.dumps(result, indent=2))
            return

        if not result["claims"]:
            console.print("[dim]No claims found.[/dim]")
            return

        table = Table(title=f"Claims ({result['count']})")
        table.add_column("ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Confidence")
        table.add_column("Title")
        table.add_column("Evidence", justify="right")
        table.add_column("Imp", justify="right")

        for c in result["claims"]:
            table.add_row(
                c["id"], c["claim_status"], c["confidence"],
                c["title"], str(c["evidence_count"]), str(c["importance"]),
            )
        console.print(table)
    finally:
        db.close()


@investigation_app.command("network")
def network(
    entry_id: str = typer.Argument(..., help="Entry ID to get network for"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="KB name"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Get the connection network for an entity."""
    plugin, db = _get_plugin_with_db()
    try:
        result = plugin._mcp_network({"entry_id": entry_id, "kb_name": kb_name})

        if output_json:
            console.print(json_mod.dumps(result, indent=2))
            return

        if "error" in result:
            console.print(f"[red]Error:[/red] {result['error']}")
            return

        console.print(f"[bold]{result['center']['title']}[/bold] ({entry_id})")
        console.print()

        if result["outlinks"]:
            console.print("[green]Outlinks:[/green]")
            for link in result["outlinks"]:
                console.print(f"  → {link}")
        else:
            console.print("[dim]No outlinks[/dim]")

        if result["backlinks"]:
            console.print("[green]Backlinks:[/green]")
            for link in result["backlinks"]:
                console.print(f"  ← {link}")
        else:
            console.print("[dim]No backlinks[/dim]")
    finally:
        db.close()


@investigation_app.command("evidence-chain")
def evidence_chain(
    claim_id: str = typer.Argument(..., help="Claim entry ID to trace"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="KB name"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Trace the evidence chain for a claim."""
    plugin, db = _get_plugin_with_db()
    try:
        result = plugin._mcp_evidence_chain({"claim_id": claim_id, "kb_name": kb_name})

        if output_json:
            console.print(json_mod.dumps(result, indent=2))
            return

        if "error" in result:
            console.print(f"[red]Error:[/red] {result['error']}")
            return

        claim = result["claim"]
        console.print(f"[bold]Claim:[/bold] {claim['title']}")
        console.print(f"  Assertion: {claim['assertion']}")
        console.print(f"  Status: {claim['claim_status']}  Confidence: {claim['confidence']}")
        console.print()

        if result["evidence_chain"]:
            console.print("[green]Evidence Chain:[/green]")
            for ev in result["evidence_chain"]:
                if ev.get("status") == "missing":
                    console.print(f"  [red]✗[/red] {ev['evidence_id']} — missing")
                else:
                    source = ev.get("source_document")
                    source_info = f" → {source['title']} ({source['reliability']})" if source else " → [dim]no source[/dim]"
                    console.print(f"  ✓ {ev['title']} ({ev['evidence_type']}){source_info}")

        if result["gaps"]:
            console.print()
            console.print("[yellow]Gaps:[/yellow]")
            for gap in result["gaps"]:
                console.print(f"  ⚠ {gap}")
    finally:
        db.close()


@investigation_app.command("qa")
def qa_report(
    kb_name: str = typer.Option(..., "--kb", "-k", help="KB name"),
    stale_days: int = typer.Option(30, "--stale-days", help="Days before unverified claims are stale"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show investigation quality metrics and warnings."""
    from .qa import compute_qa_metrics

    config = load_config()
    db = PyriteDB(config.settings.index_path)
    try:
        result = compute_qa_metrics(db, kb_name, stale_days=stale_days)

        if output_json:
            console.print(json_mod.dumps(result, indent=2))
            return

        score = result["quality_score"]
        score_color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
        console.print(f"[bold]Investigation Quality Score: [{score_color}]{score}/100[/{score_color}][/bold]")
        console.print()

        # Source tiers
        tiers = result["source_tiers"]
        console.print("[bold]Source Reliability:[/bold]")
        table = Table(show_header=True)
        table.add_column("Tier")
        table.add_column("Count", justify="right")
        for tier in ("high", "medium", "low", "unknown"):
            table.add_row(tier, str(tiers[tier]))
        table.add_row("[bold]Total[/bold]", f"[bold]{tiers['total']}[/bold]")
        console.print(table)
        console.print(f"  High-reliability: {tiers['high_pct']}%")
        console.print()

        # Claims
        claims = result["claims"]
        console.print("[bold]Claims:[/bold]")
        console.print(f"  Total: {claims['total']}")
        console.print(f"  With evidence: {claims['total'] - claims['orphans']} ({claims['coverage_pct']}%)")
        console.print(f"  Orphans (no evidence): {claims['orphans']}")
        console.print(f"  Disputed/retracted: {claims['disputed_ratio']}%")
        console.print()

        if claims["confidence"]:
            console.print("[bold]Confidence Distribution:[/bold]")
            for level in ("high", "medium", "low"):
                count = claims["confidence"].get(level, 0)
                console.print(f"  {level}: {count}")
            console.print()

        # Warnings
        if result["warnings"]:
            console.print("[bold yellow]Warnings:[/bold yellow]")
            for w in result["warnings"]:
                console.print(f"  ⚠ {w}")
        else:
            console.print("[green]No warnings.[/green]")
    finally:
        db.close()
