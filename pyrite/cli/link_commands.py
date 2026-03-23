"""
Link management commands for pyrite CLI.

Commands: check, bulk-create, suggest
"""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table

from .context import cli_context, get_config_and_db

links_app = typer.Typer(help="Link validation and inspection")
console = Console()


def _format_output(data: dict, fmt: str) -> str | None:
    """Format data using the format registry. Returns None for default (rich) output."""
    if fmt == "rich":
        return None
    from ..formats import format_response

    content, _ = format_response(data, fmt)
    return content


@links_app.command("check")
def links_check(
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB to check links from"),
    limit: int = typer.Option(500, "--limit", help="Max missing targets to show"),
    detail: bool = typer.Option(False, "--detail", help="Show per-link breakdown"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
):
    """Check for broken links (links to missing targets).

    Shows missing targets sorted by how many entries reference them.
    Use --detail to see which entries contain each broken link.
    """
    from ..services.wikilink_service import WikilinkService

    config, db = get_config_and_db()
    svc = WikilinkService(config, db)
    targets = svc.check_links(kb_name=kb_name, limit=limit)

    total_refs = sum(t["ref_count"] for t in targets)

    formatted = _format_output(
        {
            "missing_targets": len(targets),
            "total_references": total_refs,
            "targets": targets,
        },
        output_format,
    )
    if formatted is not None:
        typer.echo(formatted)
        return

    if not targets:
        console.print("[green]No broken links found.[/green]")
        return

    console.print(
        f"\n[bold]Link Check:[/bold] {len(targets)} missing target(s), {total_refs} reference(s)\n"
    )

    if detail:
        for t in targets:
            console.print(
                f"[bold]{t['target_id']}[/bold] ({t['target_kb']})"
                f" \u2014 {t['ref_count']} reference(s)"
            )
            for ref in t["references"]:
                rel = f" ({ref['relation']})" if ref.get("relation") else ""
                source = ref["source_id"]
                if ref["source_kb"] != t["target_kb"]:
                    source = f"{ref['source_kb']}/{source}"
                console.print(f"  \u2190 {source}{rel}")
            console.print()
    else:
        table = Table(show_lines=False)
        table.add_column("Missing Entry")
        table.add_column("KB")
        table.add_column("Refs", justify="right")
        table.add_column("Referenced By")

        for t in targets:
            ref_ids = [r["source_id"] for r in t["references"]]
            if len(ref_ids) > 3:
                ref_summary = ", ".join(ref_ids[:3]) + f" (+{len(ref_ids) - 3})"
            else:
                ref_summary = ", ".join(ref_ids)
            table.add_row(
                t["target_id"],
                t["target_kb"],
                str(t["ref_count"]),
                ref_summary,
            )

        console.print(table)
        if not detail:
            console.print("\nRun with [bold]--detail[/bold] for per-link breakdown.")


def _parse_link_specs(raw: str) -> list[dict]:
    """Parse YAML link specifications from a string."""
    import yaml

    data = yaml.safe_load(raw)
    if not isinstance(data, list):
        raise typer.BadParameter("YAML input must be a list of link specs")
    return data


def _validate_link_spec(spec: dict, index: int) -> list[str]:
    """Validate a single link spec dict. Returns list of error strings."""
    errors = []
    if not isinstance(spec, dict):
        return [f"Link {index}: expected a mapping, got {type(spec).__name__}"]
    if "source" not in spec:
        errors.append(f"Link {index}: missing required field 'source'")
    if "target" not in spec:
        errors.append(f"Link {index}: missing required field 'target'")
    return errors


@links_app.command("bulk-create")
def links_bulk_create(
    file: str | None = typer.Argument(
        None,
        help="YAML file with link specs, or '-' for stdin",
    ),
    kb_name: str = typer.Option(..., "--kb", "-k", help="Source KB name"),
    file_option: str | None = typer.Option(None, "--file", "-f", help="YAML file with link specs"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be created without writing"
    ),
):
    """Bulk-create links from a YAML file or stdin.

    YAML format (list of link specs):

    \b
    - source: entry-a
      target: entry-b
      relation: related_to
      note: "optional note"
      target_kb: other-kb

    Each spec requires 'source' and 'target'. Optional fields:
    'relation' (default: related_to), 'target_kb' (default: source KB), 'note'.
    """
    from datetime import UTC, datetime

    from ..storage.repository import KBRepository

    # Resolve input source: positional arg, --file option, or stdin
    input_path = file or file_option
    if input_path == "-" or (input_path is None and not sys.stdin.isatty()):
        raw = sys.stdin.read()
    elif input_path is not None:
        from pathlib import Path

        p = Path(input_path)
        if not p.exists():
            console.print(f"[red]Error:[/red] File not found: {input_path}")
            raise typer.Exit(1)
        raw = p.read_text(encoding="utf-8")
    else:
        console.print("[red]Error:[/red] Provide a YAML file path, --file, or pipe to stdin")
        raise typer.Exit(1)

    try:
        specs = _parse_link_specs(raw)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to parse YAML: {e}")
        raise typer.Exit(1)

    # Validate all specs up front
    all_errors: list[str] = []
    for i, spec in enumerate(specs):
        all_errors.extend(_validate_link_spec(spec, i))
    if all_errors:
        for err in all_errors:
            console.print(f"[red]{err}[/red]")
        raise typer.Exit(1)

    with cli_context() as (_config, _db, svc):
        kb_config = _config.get_kb(kb_name)
        if not kb_config:
            console.print(f"[red]Error:[/red] KB not found: {kb_name}")
            raise typer.Exit(1)
        if kb_config.read_only:
            console.print(f"[red]Error:[/red] KB is read-only: {kb_name}")
            raise typer.Exit(1)

        repo = KBRepository(kb_config)

        created = 0
        skipped = 0
        failed = 0
        failed_details: list[str] = []

        for i, spec in enumerate(specs):
            source_id = spec["source"]
            target_id = spec["target"]
            relation = spec.get("relation", "related_to")
            target_kb = spec.get("target_kb", kb_name)
            note = spec.get("note", "")

            try:
                entry = repo.load(source_id)
                if entry is None:
                    msg = f"Link {i}: source entry not found: {source_id}"
                    failed += 1
                    failed_details.append(msg)
                    continue

                # Check for duplicate
                is_dup = False
                for existing in entry.links:
                    if existing.target == target_id and (existing.kb or kb_name) == target_kb:
                        is_dup = True
                        break

                if is_dup:
                    skipped += 1
                    if dry_run:
                        console.print(
                            f"  [dim]skip[/dim] {source_id} --[{relation}]--> {target_id}"
                            f" (duplicate)"
                        )
                    continue

                if dry_run:
                    console.print(
                        f"  [green]create[/green] {source_id} --[{relation}]--> {target_id}"
                        f" (target_kb={target_kb})"
                    )
                    created += 1
                    continue

                # Add the link and save the file (no per-entry index)
                entry.add_link(target=target_id, relation=relation, note=note, kb=target_kb)
                entry.updated_at = datetime.now(UTC)
                repo.save(entry)
                created += 1

            except Exception as e:
                failed += 1
                failed_details.append(f"Link {i}: {e}")

        # Single index sync after all writes (skip for dry-run)
        if not dry_run and created > 0:
            svc.sync_index(kb_name)

        # Report
        label = "Dry run" if dry_run else "Bulk create"
        console.print(
            f"\n[bold]{label}:[/bold] {created} created, {skipped} skipped, {failed} failed"
        )
        for detail in failed_details:
            console.print(f"  [red]{detail}[/red]")


def _build_suggest_query(entry: dict) -> str:
    """Build an FTS5 OR query from an entry's title words and tags.

    Uses OR to find entries sharing *any* term, which gives broader recall
    and lets FTS5 rank by overlap.
    """
    import re

    tokens: list[str] = []
    title = entry.get("title", "")
    if title:
        # Split title into words, keep only alphanumeric tokens
        tokens.extend(w for w in re.split(r"\W+", title) if w and len(w) > 2)
    tags = entry.get("tags", [])
    if tags:
        tokens.extend(t for t in tags if t)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        lower = t.lower()
        if lower not in seen:
            seen.add(lower)
            unique.append(t)
    return " OR ".join(unique)


def _suggest_links(
    entry_id: str,
    kb_name: str,
    target_kb: str | None,
    limit: int,
) -> list[dict]:
    """Find entries related to the given entry using FTS5 keyword search.

    Returns a list of candidate dicts with id, kb_name, title, entry_type,
    score, and snippet.
    """
    from ..services.kb_service import KBService
    from ..services.search_service import SearchService

    config, db = get_config_and_db()
    try:
        svc = KBService(config, db)
        entry = svc.get_entry(entry_id, kb_name=kb_name)
        if entry is None:
            return []

        query = _build_suggest_query(entry)
        if not query.strip():
            return []

        search_svc = SearchService(db, settings=config.settings)
        search_kb = target_kb or kb_name

        # Fetch extra results so we can filter out self and existing links
        raw_results = search_svc.search(
            query=query,
            kb_name=search_kb,
            limit=limit + 20,
            mode="keyword",
        )

        # Collect existing link targets to exclude
        existing_targets = set()
        for link in entry.get("outlinks", []) or []:
            existing_targets.add(link.get("id", ""))
        for link in entry.get("links", []) or []:
            existing_targets.add(link.get("target_id") or link.get("target", ""))

        candidates = []
        for r in raw_results:
            rid = r.get("id", "")
            if rid == entry_id:
                continue
            if rid in existing_targets:
                continue
            candidates.append(
                {
                    "id": rid,
                    "kb_name": r.get("kb_name", search_kb),
                    "title": r.get("title", ""),
                    "entry_type": r.get("entry_type", ""),
                    "score": round(r.get("rank", 0.0), 4),
                    "snippet": (r.get("snippet") or "")[:150],
                }
            )
            if len(candidates) >= limit:
                break

        return candidates
    finally:
        db.close()


@links_app.command("suggest")
def links_suggest(
    entry_id: str = typer.Argument(..., help="Entry ID to find suggestions for"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="KB containing the entry"),
    target_kb: str | None = typer.Option(
        None, "--target-kb", help="KB to search for candidates (default: same as --kb)"
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="Max number of suggestions"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: json, rich, markdown, csv, yaml"
    ),
):
    """Suggest related entries that could be linked.

    Uses FTS5 keyword search on title and tags to find entries
    that are likely related. No LLM required.

    \b
    Examples:
        pyrite links suggest my-entry --kb notes
        pyrite links suggest my-entry --kb notes --target-kb other-kb --format json
    """
    from ..services.kb_service import KBService

    config, db = get_config_and_db()
    try:
        svc = KBService(config, db)
        entry = svc.get_entry(entry_id, kb_name=kb_name)
    finally:
        db.close()

    if entry is None:
        console.print(f"[red]Error:[/red] Entry not found: {entry_id} (kb={kb_name})")
        raise typer.Exit(1)

    candidates = _suggest_links(entry_id, kb_name, target_kb, limit)

    data = {
        "entry_id": entry_id,
        "kb_name": kb_name,
        "target_kb": target_kb or kb_name,
        "count": len(candidates),
        "suggestions": candidates,
    }

    formatted = _format_output(data, output_format)
    if formatted is not None:
        typer.echo(formatted)
        return

    if not candidates:
        console.print("[dim]No suggestions found.[/dim]")
        return

    console.print(
        f"\n[bold]Link suggestions for[/bold] {entry_id}"
        f" [dim](target KB: {target_kb or kb_name})[/dim]\n"
    )

    table = Table(show_lines=False)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Entry ID")
    table.add_column("Title")
    table.add_column("Type", style="dim")
    table.add_column("Score", justify="right")

    for i, c in enumerate(candidates, 1):
        table.add_row(
            str(i),
            c["id"],
            c["title"][:60],
            c["entry_type"],
            str(c["score"]),
        )

    console.print(table)
