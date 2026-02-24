"""Markdown format importer -- parse markdown files with YAML frontmatter."""

import re
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def import_markdown(data: str | bytes) -> list[dict[str, Any]]:
    """Parse one or more markdown entries with YAML frontmatter.

    Supports:
    - Single entry: one frontmatter block + body
    - Multiple entries: separated by ``---`` on its own line (after the first block)
    """
    if isinstance(data, bytes):
        data = data.decode("utf-8")

    entries = []
    # Split on document separator (triple dash on own line, not frontmatter)
    # Strategy: parse first entry, then check for more
    remaining = data.strip()

    while remaining:
        entry = _parse_single_md(remaining)
        if entry:
            entries.append(entry)
        # Find next entry separator
        # After the first frontmatter+body, look for next ---\n that starts a new entry
        match = _FRONTMATTER_RE.match(remaining)
        if match:
            after_fm = remaining[match.end() :]
            # Find next document separator
            next_sep = re.search(r"\n---\s*\n", after_fm)
            if next_sep:
                remaining = after_fm[next_sep.end() :]
                # Re-add frontmatter markers
                remaining = "---\n" + remaining if not remaining.startswith("---") else remaining
            else:
                break
        else:
            break

    return entries


def _parse_single_md(text: str) -> dict[str, Any] | None:
    """Parse a single markdown entry with frontmatter."""
    from pyrite.utils.yaml import load_yaml

    match = _FRONTMATTER_RE.match(text)
    if not match:
        # No frontmatter -- treat entire text as body
        if text.strip():
            # Try to extract title from first heading
            lines = text.strip().split("\n")
            title = "Untitled"
            body = text.strip()
            if lines[0].startswith("# "):
                title = lines[0][2:].strip()
                body = "\n".join(lines[1:]).strip()
            return {
                "id": "",
                "title": title,
                "body": body,
                "entry_type": "note",
                "tags": [],
            }
        return None

    frontmatter_text = match.group(1)
    body = text[match.end() :].strip()

    try:
        fm = load_yaml(frontmatter_text)
    except Exception:
        fm = {}

    if not isinstance(fm, dict):
        fm = {}

    return {
        "id": fm.get("id", ""),
        "title": fm.get("title", "Untitled"),
        "body": body,
        "entry_type": fm.get("type", fm.get("entry_type", "note")),
        "tags": fm.get("tags", []),
        **{
            k: v
            for k, v in fm.items()
            if k not in ("id", "title", "type", "entry_type", "tags", "body")
        },
    }
