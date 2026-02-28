"""
QA validation commands for pyrite CLI.

Commands: validate, status
"""

import typer
from rich.console import Console
from rich.table import Table

from ..config import load_config
from ..storage.database import PyriteDB

qa_app = typer.Typer(help="Quality assurance validation")
console = Console()


def _format_output(data: dict, fmt: str) -> str | None:
    """Format data using the format registry. Returns None for default (rich) output."""
    if fmt == "rich":
        return None
    from ..formats import format_response

    content, _ = format_response(data, fmt)
    return content


@qa_app.command("validate")
def qa_validate(
    kb_name: str | None = typer.Argument(None, help="KB to validate (all if omitted)"),
    entry: str | None = typer.Option(None, "--entry", "-e", help="Validate single entry by ID"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
    severity: str | None = typer.Option(
        None, "--severity", "-s", help="Minimum severity filter: error, warning, info"
    ),
):
    """Validate KB structural integrity.

    Checks for missing titles, empty bodies, broken links, orphan entries,
    invalid dates, importance out of range, and schema violations.
    """
    from ..services.qa_service import QAService

    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        qa = QAService(config, db)

        if entry and kb_name:
            result = qa.validate_entry(entry, kb_name)
            issues = result["issues"]
        elif kb_name:
            result = qa.validate_kb(kb_name)
            issues = result["issues"]
        else:
            result = qa.validate_all()
            issues = []
            for kb in result["kbs"]:
                issues.extend(kb["issues"])

        # Filter by severity
        if severity:
            severity_order = {"error": 0, "warning": 1, "info": 2}
            min_level = severity_order.get(severity, 2)
            issues = [
                i for i in issues if severity_order.get(i.get("severity", "info"), 2) <= min_level
            ]

        formatted = _format_output({"issues": issues, "count": len(issues)}, output_format)
        if formatted is not None:
            typer.echo(formatted)
            return

        # Rich output
        if not issues:
            console.print("[green]No issues found.[/green]")
            return

        table = Table(title="QA Issues")
        table.add_column("KB", style="dim")
        table.add_column("Entry", style="cyan")
        table.add_column("Rule")
        table.add_column("Severity")
        table.add_column("Message")

        severity_styles = {"error": "red", "warning": "yellow", "info": "dim"}

        for issue in issues:
            sev = issue.get("severity", "info")
            table.add_row(
                issue.get("kb_name", ""),
                issue.get("entry_id", ""),
                issue.get("rule", ""),
                f"[{severity_styles.get(sev, 'dim')}]{sev}[/{severity_styles.get(sev, 'dim')}]",
                issue.get("message", ""),
            )

        console.print(table)

        # Summary
        error_count = sum(1 for i in issues if i.get("severity") == "error")
        warn_count = sum(1 for i in issues if i.get("severity") == "warning")
        info_count = sum(1 for i in issues if i.get("severity") == "info")
        console.print(
            f"\n[bold]Total:[/bold] {len(issues)} issues "
            f"([red]{error_count} errors[/red], "
            f"[yellow]{warn_count} warnings[/yellow], "
            f"[dim]{info_count} info[/dim])"
        )

        if error_count > 0:
            raise typer.Exit(1)

    finally:
        db.close()


@qa_app.command("status")
def qa_status(
    kb_name: str | None = typer.Argument(None, help="KB to check (all if omitted)"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """Show QA status dashboard with issue counts."""
    from ..services.qa_service import QAService

    config = load_config()
    db = PyriteDB(config.settings.index_path)

    try:
        qa = QAService(config, db)
        status = qa.get_status(kb_name=kb_name)

        formatted = _format_output(status, output_format)
        if formatted is not None:
            typer.echo(formatted)
            return

        # Rich output
        console.print("\n[bold]QA Status[/bold]")
        console.print(f"  Total entries: {status['total_entries']}")
        console.print(f"  Total issues: {status['total_issues']}")

        if status["issues_by_severity"]:
            console.print("\n[bold]By Severity:[/bold]")
            for sev, count in sorted(status["issues_by_severity"].items()):
                style = {"error": "red", "warning": "yellow", "info": "dim"}.get(sev, "")
                console.print(f"  [{style}]{sev}: {count}[/{style}]")

        if status["issues_by_rule"]:
            console.print("\n[bold]By Rule:[/bold]")
            for rule, count in sorted(status["issues_by_rule"].items(), key=lambda x: -x[1]):
                console.print(f"  {rule}: {count}")

    finally:
        db.close()
