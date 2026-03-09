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
        "json", "--format", help="Output format: json, rich, markdown, csv, yaml"
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
    max_age: int = typer.Option(
        24, "--max-age", help="Skip entries assessed within N hours (0 = reassess all)"
    ),
    create_tasks: bool = typer.Option(
        False, "--create-tasks", help="Create tasks for failed assessments"
    ),
    output_format: str = typer.Option(
        "json", "--format", help="Output format: json, rich, markdown, csv, yaml"
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
        "json", "--format", help="Output format: json, rich, markdown, csv, yaml"
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


@qa_app.command("checkers")
def qa_checkers(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="Show rubric coverage for a specific KB"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: json, rich"
    ),
):
    """List available rubric checkers and per-KB coverage.

    Without --kb, lists all registered checkers (core + plugins).
    With --kb, shows which rubric items are checker-bound, schema-covered,
    or judgment-only for each type in that KB.
    """

    if kb_name:
        _show_kb_coverage(kb_name, output_format)
    else:
        _show_all_checkers(output_format)


def _show_all_checkers(output_format: str) -> None:
    """List all registered checkers (core + plugins)."""
    from ..plugins.registry import get_registry
    from ..services.rubric_checkers import NAMED_CHECKERS

    all_checkers = get_registry().get_all_rubric_checkers()

    # Determine which are core vs plugin
    core_names = set(NAMED_CHECKERS.keys())

    if output_format == "json":
        import json

        data = {
            "core": sorted(core_names),
            "plugin": sorted(set(all_checkers.keys()) - core_names),
        }
        typer.echo(json.dumps(data, indent=2))
        return

    # Rich output
    table = Table(title="Available Rubric Checkers")
    table.add_column("Name", style="cyan")
    table.add_column("Source", style="dim")
    table.add_column("Description")

    for name in sorted(all_checkers.keys()):
        fn = all_checkers[name]
        source = "core" if name in core_names else name.split(".")[0] if "." in name else "plugin"
        doc = (fn.__doc__ or "").split("\n")[0].strip()
        table.add_row(name, source, doc)

    console.print(table)
    console.print(f"\n[bold]{len(all_checkers)}[/bold] checkers available")


def _show_kb_coverage(kb_name: str, output_format: str) -> None:
    """Show rubric coverage for a specific KB."""
    from ..plugins.registry import get_registry
    from ..schema.core_types import SYSTEM_INTENT, resolve_type_metadata
    from .context import cli_context

    with cli_context() as (config, db, svc):
        kb_config = config.get_kb(kb_name)
        if not kb_config:
            console.print(f"[red]KB '{kb_name}' not found[/red]")
            raise typer.Exit(1)

        kb_schema = kb_config.kb_schema
        all_checkers = get_registry().get_all_rubric_checkers()

        # Get all entry types in this KB
        type_rows = db.execute_sql(
            "SELECT DISTINCT entry_type FROM entry WHERE kb_name = :kb",
            {"kb": kb_name},
        )
        entry_types = sorted(row["entry_type"] for row in type_rows if row["entry_type"])

        total_checker = 0
        total_schema = 0
        total_judgment = 0

        def _count_item(kind: str) -> None:
            nonlocal total_checker, total_schema, total_judgment
            if kind == "checker":
                total_checker += 1
            elif kind == "schema":
                total_schema += 1
            else:
                total_judgment += 1

        # System-level rubric (always applies)
        system_rubric = SYSTEM_INTENT.get("evaluation_rubric", [])
        if system_rubric:
            console.print(f"\n[bold]System rubric ({len(system_rubric)} items):[/bold]")
            for item in system_rubric:
                label, kind = _classify_rubric_item(item, all_checkers)
                _print_rubric_line(label, kind, item)
                _count_item(kind)

        # KB-level rubric
        kb_rubric = (kb_schema.evaluation_rubric if kb_schema else []) or []
        if kb_rubric:
            console.print(f"\n[bold]KB-level rubric ({len(kb_rubric)} items):[/bold]")
            for item in kb_rubric:
                label, kind = _classify_rubric_item(item, all_checkers)
                _print_rubric_line(label, kind, item)
                _count_item(kind)

        # Per-type rubric
        for entry_type in entry_types:
            type_meta = resolve_type_metadata(entry_type, kb_schema)
            rubric = type_meta.get("evaluation_rubric", [])
            if not rubric:
                continue
            console.print(f"\n[bold]Type: {entry_type} ({len(rubric)} items):[/bold]")
            for item in rubric:
                label, kind = _classify_rubric_item(item, all_checkers)
                _print_rubric_line(label, kind, item)
                _count_item(kind)

        console.print(
            f"\n[bold]Summary:[/bold] {total_checker} checker-bound, "
            f"{total_schema} schema-covered, {total_judgment} judgment-only"
        )


def _classify_rubric_item(
    item: str | dict, checkers: dict
) -> tuple[str, str]:
    """Classify a rubric item. Returns (display_text, kind)."""
    if isinstance(item, dict):
        text = item.get("text", "")
        if item.get("covered_by"):
            return text, "schema"
        checker_name = item.get("checker")
        if checker_name:
            if checker_name in checkers:
                return text, "checker"
            return text, "unknown"
        return text, "judgment"
    # Plain string — always judgment-only
    return item, "judgment"


def _print_rubric_line(text: str, kind: str, item: str | dict) -> None:
    """Print a single rubric item with classification tag."""
    styles = {
        "checker": "[green][checker][/green]",
        "schema": "[blue][schema][/blue]",
        "judgment": "[yellow][judgment][/yellow]",
        "unknown": "[red][unknown][/red]",
    }
    tag = styles.get(kind, "[dim][?][/dim]")
    checker_info = ""
    if isinstance(item, dict) and item.get("checker"):
        checker_info = f" → {item['checker']}"
    console.print(f"  {tag}  \"{text}\"{checker_info}")


@qa_app.command("stale")
def qa_stale(
    kb_name: str = typer.Argument(..., help="KB to check for stale entries"),
    max_age: int = typer.Option(90, "--max-age", "-a", help="Days since last update to consider stale"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
):
    """Find entries that haven't been updated recently.

    Reports entries older than --max-age days. Historical types (ADR, event,
    timeline) are exempt since they represent past records.
    """
    ctx = cli_context()
    from ..services.qa_service import QAService

    svc = QAService(ctx.config, ctx.db)
    results = svc.find_stale(kb_name, max_age_days=max_age)

    data = {"kb_name": kb_name, "max_age_days": max_age, "stale_count": len(results), "entries": results}

    formatted = _format_output(data, output_format)
    if formatted:
        console.print(formatted)
        return

    if not results:
        console.print(f"[green]No stale entries in '{kb_name}' (threshold: {max_age} days)[/green]")
        return

    table = Table(title=f"Stale entries in '{kb_name}' (>{max_age} days)")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Title")
    table.add_column("Days Stale", justify="right", style="yellow")

    for entry in results:
        table.add_row(entry["entry_id"], entry["entry_type"], entry["title"], str(entry["days_stale"]))

    console.print(table)
    console.print(f"\n[yellow]{len(results)} stale entries found[/yellow]")


@qa_app.command("compact")
def qa_compact(
    kb_name: str = typer.Argument(..., help="KB to check for archival candidates"),
    min_age: int = typer.Option(90, "--min-age", "-a", help="Minimum days old to be a candidate"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
):
    """Find entries that are candidates for archival.

    Identifies completed backlog items and old orphan entries (no links, low
    importance) that could be archived to reduce noise.

    This is a dry-run report — no entries are modified.
    """
    ctx = cli_context()
    from ..services.qa_service import QAService

    svc = QAService(ctx.config, ctx.db)
    results = svc.find_archival_candidates(kb_name, min_age_days=min_age)

    data = {"kb_name": kb_name, "min_age_days": min_age, "candidate_count": len(results), "entries": results}

    formatted = _format_output(data, output_format)
    if formatted:
        console.print(formatted)
        return

    if not results:
        console.print(f"[green]No archival candidates in '{kb_name}' (threshold: {min_age} days)[/green]")
        return

    table = Table(title=f"Archival candidates in '{kb_name}' (>{min_age} days)")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Title")
    table.add_column("Reason", style="yellow")
    table.add_column("Days Old", justify="right")

    for entry in results:
        table.add_row(
            entry["entry_id"],
            entry["entry_type"],
            entry["title"],
            entry["reason"],
            str(entry["days_old"]),
        )

    console.print(table)
    console.print(f"\n[yellow]{len(results)} archival candidates found[/yellow]")
    console.print("[dim]Use 'pyrite update <id> -k <kb> --lifecycle archived' to archive entries[/dim]")
