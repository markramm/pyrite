"""
NotebookLM Renderer

Renders KB entries as enriched, self-contained markdown optimized for
Google NotebookLM ingestion. Handles source redaction, metadata display,
connection rendering, and bundling for the 50-source limit.
"""

from collections import defaultdict
from enum import Enum
from typing import Any

from ..models.base import Entry
from ..schema import Source


class SourceMode(Enum):
    """How to handle source visibility in exports."""

    PUBLIC = "public"  # Render non-restricted sources only
    FULL = "full"  # Render all sources including restricted
    REDACT = "redact"  # Show restricted sources as [source redacted]


class BundleStrategy(Enum):
    """How to group entries into files for NotebookLM's source limit."""

    AUTO = "auto"  # ≤50 entries: one-per-entry; >50: by-type
    NONE = "none"  # One file per entry
    BY_TYPE = "by-type"  # Group by entry type
    SINGLE = "single"  # Everything in one document


# Fields from to_frontmatter() that are internal / not useful to readers
_SKIP_FIELDS = frozenset(
    {
        "id",
        "type",
        "title",
        "_schema_version",
        "created_at",
        "updated_at",
        "sources",
        "links",
        "provenance",
        "metadata",
        "aliases",
    }
)

# Max entries before AUTO switches from NONE to BY_TYPE
_AUTO_THRESHOLD = 50


def render_entry(
    entry: Entry,
    source_mode: SourceMode = SourceMode.PUBLIC,
) -> str:
    """Render a single entry as enriched markdown for NotebookLM.

    Structure:
        # Title (type)
        **field:** value  (type-specific fields from to_frontmatter)

        Body content

        ## Metadata        (if entry.metadata is non-empty)
        **key:** value

        ## Sources          (if entry has sources, respecting source_mode)
        - "Title" -- Outlet, Date (confidence)

        ## Connections      (if entry has links)
        - -> Target (relation)
    """
    fm = entry.to_frontmatter()
    parts: list[str] = []

    # --- Title ---
    entry_type = fm.get("type", entry.entry_type)
    parts.append(f"# {entry.title} ({entry_type})")
    parts.append("")

    # --- Type-specific fields ---
    display_fields = _extract_display_fields(fm)
    if display_fields:
        for key, value in display_fields.items():
            parts.append(f"**{key}:** {_format_value(value)}")
        parts.append("")

    # --- Body ---
    if entry.body:
        parts.append(entry.body)
        parts.append("")

    # --- Metadata section ---
    if entry.metadata:
        parts.append("## Metadata")
        parts.append("")
        for key, value in entry.metadata.items():
            parts.append(f"**{key}:** {_format_value(value)}")
        parts.append("")

    # --- Sources section ---
    source_lines = _render_sources(entry.sources, source_mode)
    if source_lines:
        parts.append("## Sources")
        parts.append("")
        parts.extend(source_lines)
        parts.append("")

    # --- Connections section ---
    if entry.links:
        parts.append("## Connections")
        parts.append("")
        for link in entry.links:
            line = f"- {link.target} ({link.relation})"
            if link.note:
                line += f" -- {link.note}"
            parts.append(line)
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _extract_display_fields(fm: dict[str, Any]) -> dict[str, Any]:
    """Extract fields worth displaying from frontmatter, skipping internals."""
    return {k: v for k, v in fm.items() if k not in _SKIP_FIELDS and v}


def _format_value(value: Any) -> str:
    """Format a frontmatter value for display."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _render_sources(sources: list[Source], mode: SourceMode) -> list[str]:
    """Render source list respecting the visibility mode."""
    lines: list[str] = []
    for source in sources:
        is_restricted = source.access in ("restricted", "offline")

        if mode == SourceMode.PUBLIC and is_restricted:
            continue

        if mode == SourceMode.REDACT and is_restricted:
            lines.append("- [source redacted]")
            continue

        # Build source line
        parts = [f'- "{source.title}"']
        if source.outlet:
            parts.append(f" -- {source.outlet}")
        if source.date:
            parts.append(f", {source.date}")
        if source.confidence and source.confidence != "unverified":
            parts.append(f" ({source.confidence})")
        if source.url:
            parts.append(f" {source.url}")
        lines.append("".join(parts))

    return lines


def bundle_entries(
    entries: list[Entry],
    strategy: BundleStrategy = BundleStrategy.AUTO,
    source_mode: SourceMode = SourceMode.PUBLIC,
) -> dict[str, str]:
    """Bundle rendered entries into files according to strategy.

    Returns:
        Dict of filename -> content. Does not include the manifest
        (use generate_manifest() separately).
    """
    if strategy == BundleStrategy.AUTO:
        strategy = (
            BundleStrategy.NONE if len(entries) <= _AUTO_THRESHOLD else BundleStrategy.BY_TYPE
        )

    if strategy == BundleStrategy.NONE:
        return _bundle_none(entries, source_mode)
    elif strategy == BundleStrategy.BY_TYPE:
        return _bundle_by_type(entries, source_mode)
    elif strategy == BundleStrategy.SINGLE:
        return _bundle_single(entries, source_mode)
    else:
        return _bundle_none(entries, source_mode)


def _bundle_none(entries: list[Entry], source_mode: SourceMode) -> dict[str, str]:
    """One file per entry."""
    files: dict[str, str] = {}
    for entry in entries:
        filename = f"{entry.id}.md"
        files[filename] = render_entry(entry, source_mode=source_mode)
    return files


def _bundle_by_type(entries: list[Entry], source_mode: SourceMode) -> dict[str, str]:
    """Group entries by type into one file per type."""
    groups: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        groups[entry.entry_type].append(entry)

    files: dict[str, str] = {}
    for entry_type, type_entries in sorted(groups.items()):
        parts: list[str] = []
        for entry in type_entries:
            parts.append(render_entry(entry, source_mode=source_mode))
            parts.append("---")
            parts.append("")
        filename = f"{entry_type}.md"
        files[filename] = "\n".join(parts).rstrip() + "\n"
    return files


def _bundle_single(entries: list[Entry], source_mode: SourceMode) -> dict[str, str]:
    """Everything in one document."""
    parts: list[str] = []
    for entry in entries:
        parts.append(render_entry(entry, source_mode=source_mode))
        parts.append("---")
        parts.append("")
    content = "\n".join(parts).rstrip() + "\n"
    return {"all_entries.md": content}


def generate_manifest(
    entries: list[Entry],
    title: str = "Exported Knowledge Base",
) -> str:
    """Generate a manifest/table-of-contents document.

    This is designed to be the first source uploaded to NotebookLM,
    giving it narrative framing for all the other sources.
    """
    # Count by type
    type_counts: dict[str, int] = defaultdict(int)
    for entry in entries:
        type_counts[entry.entry_type] += 1

    parts: list[str] = []
    parts.append(f"# {title}")
    parts.append("")
    parts.append(
        "This notebook contains exported knowledge base entries. "
        "Use this as a guide to navigate the included sources."
    )
    parts.append("")

    # Summary
    parts.append("## Summary")
    parts.append("")
    parts.append(f"**Total entries:** {len(entries)}")
    parts.append("")
    for entry_type, count in sorted(type_counts.items()):
        parts.append(f"- {count} {entry_type} entries")
    parts.append("")

    # Entry index table
    parts.append("## Entry Index")
    parts.append("")
    parts.append("| Entry | Type | Summary |")
    parts.append("|-------|------|---------|")
    for entry in entries:
        summary = entry.summary or ""
        if len(summary) > 80:
            summary = summary[:77] + "..."
        parts.append(f"| {entry.title} | {entry.entry_type} | {summary} |")
    parts.append("")

    return "\n".join(parts).rstrip() + "\n"
