"""
QA validation and assessment commands for pyrite CLI.

Commands: validate, status, assess
"""

import typer
from rich.console import Console
from rich.table import Table

from .context import cli_context

qa_app = typer.Typer(help="Quality assurance validation and assessment")
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

    with cli_context() as (config, db, svc):
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


@qa_app.command("assess")
def qa_assess(
    kb_name: str = typer.Argument(..., help="KB to assess"),
    entry: str | None = typer.Option(None, "--entry", "-e", help="Assess single entry by ID"),
    tier: int = typer.Option(1, "--tier", "-t", help="Assessment tier (1=structural)"),
    max_age: int = typer.Option(24, "--max-age", help="Skip entries assessed within N hours (0 = reassess all)"),
    create_tasks: bool = typer.Option(False, "--create-tasks", help="Create tasks for failed assessments"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """Run QA assessment on entries, creating assessment records.

    Assesses entry quality and creates qa_assessment entries in the KB.
    Use --create-tasks to auto-generate tasks for failures.
    """
    from ..services.qa_service import QAService

    with cli_context() as (config, db, svc):
        qa = QAService(config, db)

        if entry:
            result = qa.assess_entry(entry, kb_name, tier=tier, create_task_on_fail=create_tasks)
            data = {
                "assessment_id": result["assessment_id"],
                "target_entry": result["target_entry"],
                "qa_status": result["qa_status"],
                "issues_found": result["issues_found"],
            }
        else:
            result = qa.assess_kb(
                kb_name, tier=tier, max_age_hours=max_age, create_task_on_fail=create_tasks
            )
            data = {
                "kb_name": result["kb_name"],
                "assessed": result["assessed"],
                "skipped": result["skipped"],
                "results": [
                    {
                        "assessment_id": r["assessment_id"],
                        "target_entry": r["target_entry"],
                        "qa_status": r["qa_status"],
                        "issues_found": r["issues_found"],
                    }
                    for r in result["results"]
                ],
            }

        formatted = _format_output(data, output_format)
        if formatted is not None:
            typer.echo(formatted)
            return

        # Rich output
        if entry:
            status_style = {"pass": "green", "warn": "yellow", "fail": "red"}.get(
                result["qa_status"], ""
            )
            console.print(
                f"[bold]Assessment:[/bold] {result['assessment_id']}\n"
                f"  Target: {result['target_entry']}\n"
                f"  Status: [{status_style}]{result['qa_status']}[/{status_style}]\n"
                f"  Issues: {result['issues_found']}"
            )
        else:
            console.print(
                f"[bold]KB Assessment: {kb_name}[/bold]\n"
                f"  Assessed: {result['assessed']}\n"
                f"  Skipped: {result['skipped']}"
            )
            if result["results"]:
                table = Table(title="Results")
                table.add_column("Entry", style="cyan")
                table.add_column("Status")
                table.add_column("Issues", justify="right")

                status_styles = {"pass": "green", "warn": "yellow", "fail": "red"}
                for r in result["results"]:
                    s = r["qa_status"]
                    table.add_row(
                        r["target_entry"],
                        f"[{status_styles.get(s, '')}]{s}[/{status_styles.get(s, '')}]",
                        str(r["issues_found"]),
                    )
                console.print(table)


@qa_app.command("status")
def qa_status(
    kb_name: str | None = typer.Argument(None, help="KB to check (all if omitted)"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """Show QA status dashboard with issue counts and coverage."""
    from ..services.qa_service import QAService

    with cli_context() as (config, db, svc):
        qa = QAService(config, db)
        status = qa.get_status(kb_name=kb_name)

        # Add coverage stats if a specific KB is given
        if kb_name:
            status["coverage"] = qa.get_coverage(kb_name)

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

        if "coverage" in status:
            cov = status["coverage"]
            console.print("\n[bold]Coverage:[/bold]")
            console.print(f"  Total entries: {cov['total']}")
            console.print(f"  Assessed: {cov['assessed']}")
            console.print(f"  Unassessed: {cov['unassessed']}")
            console.print(f"  Coverage: {cov['coverage_pct']}%")
            if cov.get("by_status"):
                for s, cnt in cov["by_status"].items():
                    style = {"pass": "green", "warn": "yellow", "fail": "red"}.get(s, "")
                    console.print(f"    [{style}]{s}: {cnt}[/{style}]")
