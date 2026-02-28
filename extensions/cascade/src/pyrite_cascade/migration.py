"""Migration scripts for Cascade Series KB import.

Run once on copied files to normalize frontmatter before Pyrite indexing.
"""

import re
from pathlib import Path

# Folder prefixes to strip from wikilinks in research KB
_WIKILINK_PREFIXES = (
    "actors",
    "organizations",
    "events",
    "themes",
    "scenes",
    "victims",
    "statistics",
    "mechanisms",
    "sources",
    "capture-lanes",
    "research-notes",
)

_WIKILINK_PREFIX_RE = re.compile(
    r"\[\[(" + "|".join(re.escape(p) for p in _WIKILINK_PREFIXES) + r")/",
)

# Frontmatter block regex (matches content between first --- and second ---)
_FRONTMATTER_RE = re.compile(r"\A(---\n)(.*?)(---\n)", re.DOTALL)


def inject_ids(kb_path: str | Path) -> dict[str, str]:
    """Add id: <filename-stem> to research KB files that lack an id field.

    Returns dict mapping filename to injected ID for reporting.
    """
    kb_path = Path(kb_path)
    injected: dict[str, str] = {}
    seen_ids: dict[str, Path] = {}
    collisions: list[str] = []

    for md_file in sorted(kb_path.rglob("*.md")):
        if md_file.name.startswith("_"):
            continue
        stem = md_file.stem
        content = md_file.read_text(encoding="utf-8")

        # Check for ID collisions
        if stem in seen_ids:
            collisions.append(f"ID collision: '{stem}' in {seen_ids[stem]} and {md_file}")
        seen_ids[stem] = md_file

        m = _FRONTMATTER_RE.match(content)
        if not m:
            continue

        fm_block = m.group(2)

        # Skip if already has an id field
        if re.search(r"^id:\s", fm_block, re.MULTILINE):
            continue

        # Inject id after the opening ---
        new_content = m.group(1) + f"id: {stem}\n" + fm_block + m.group(3) + content[m.end():]
        md_file.write_text(new_content, encoding="utf-8")
        injected[str(md_file)] = stem

    if collisions:
        for c in collisions:
            print(f"WARNING: {c}")

    return injected


def normalize_wikilinks(kb_path: str | Path) -> int:
    """Strip folder prefixes from wikilinks in research KB files.

    [[actors/powell-lewis]] → [[powell-lewis]]
    [[organizations/ALEC]] → [[ALEC]]

    Returns count of substitutions made.
    """
    kb_path = Path(kb_path)
    total_subs = 0

    for md_file in sorted(kb_path.rglob("*.md")):
        if md_file.name.startswith("_"):
            continue
        content = md_file.read_text(encoding="utf-8")
        new_content, n = _WIKILINK_PREFIX_RE.subn("[[", content)
        if n > 0:
            md_file.write_text(new_content, encoding="utf-8")
            total_subs += n

    return total_subs


def normalize_research_frontmatter(kb_path: str | Path) -> dict[str, int]:
    """Normalize frontmatter in research KB files.

    - essay_type: mechanism → type: mechanism
    - event_date: X → date: X (for events)
    - type: organization → type: cascade_org
    - Normalize research_status values
    - Normalize era values (strip quotes)

    Returns counts of each transformation.
    """
    kb_path = Path(kb_path)
    counts: dict[str, int] = {
        "essay_type_to_type": 0,
        "event_date_to_date": 0,
        "org_to_cascade_org": 0,
        "research_status_normalized": 0,
    }

    # Valid research_status values and their mappings
    status_map = {
        "stub": "stub",
        "in-progress": "in-progress",
        "in_progress": "in-progress",
        "complete": "complete",
        "comprehensive": "comprehensive",
        "active": "in-progress",
    }

    for md_file in sorted(kb_path.rglob("*.md")):
        if md_file.name.startswith("_"):
            continue
        content = md_file.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(content)
        if not m:
            continue

        fm = m.group(2)
        body = content[m.end():]
        changed = False

        # essay_type → type
        new_fm, n = re.subn(r"^essay_type:\s*", "type: ", fm, flags=re.MULTILINE)
        if n:
            fm = new_fm
            changed = True
            counts["essay_type_to_type"] += n

        # event_date → date (only if no date: field already exists)
        if re.search(r"^event_date:", fm, re.MULTILINE) and not re.search(r"^date:", fm, re.MULTILINE):
            new_fm, n = re.subn(r"^event_date:", "date:", fm, flags=re.MULTILINE)
            if n:
                fm = new_fm
                changed = True
                counts["event_date_to_date"] += n

        # type: organization → type: cascade_org
        new_fm, n = re.subn(r"^type:\s*organization\s*$", "type: cascade_org", fm, flags=re.MULTILINE)
        if n:
            fm = new_fm
            changed = True
            counts["org_to_cascade_org"] += n

        # Normalize research_status (strip quotes, map synonyms)
        rs_match = re.search(r'^(research_status:\s*)(["\']?)([^"\'\n]+)\2\s*$', fm, re.MULTILINE)
        if rs_match:
            raw = rs_match.group(3).strip().lower()
            normalized = status_map.get(raw, raw)
            has_quotes = bool(rs_match.group(2))
            value_changed = normalized != raw
            if has_quotes or value_changed:
                fm = fm[:rs_match.start()] + f"research_status: {normalized}" + fm[rs_match.end():]
                changed = True
                counts["research_status_normalized"] += 1

        if changed:
            new_content = m.group(1) + fm + m.group(3) + body
            md_file.write_text(new_content, encoding="utf-8")

    return counts


def normalize_timeline_frontmatter(kb_path: str | Path) -> dict[str, int]:
    """Normalize frontmatter in timeline KB files.

    - Add type: timeline_event to all files
    - Strip quotes from date values (YAML-safe already)

    Uses fast regex — no full YAML parse for 4,144 files.
    Returns counts of transformations.
    """
    kb_path = Path(kb_path)
    counts: dict[str, int] = {
        "type_added": 0,
        "date_unquoted": 0,
    }

    for md_file in sorted(kb_path.rglob("*.md")):
        if md_file.name.startswith("_"):
            continue
        content = md_file.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(content)
        if not m:
            continue

        fm = m.group(2)
        body = content[m.end():]
        changed = False

        # Add type: timeline_event if missing
        if not re.search(r"^type:", fm, re.MULTILINE):
            fm = "type: timeline_event\n" + fm
            changed = True
            counts["type_added"] += 1

        # Unquote date values: date: '2024-01-15' → date: 2024-01-15
        new_fm, n = re.subn(
            r"^(date:\s*)['\"](\d{4}-\d{2}-\d{2})['\"]",
            r"\g<1>\2",
            fm,
            flags=re.MULTILINE,
        )
        if n:
            fm = new_fm
            changed = True
            counts["date_unquoted"] += n

        if changed:
            new_content = m.group(1) + fm + m.group(3) + body
            md_file.write_text(new_content, encoding="utf-8")

    return counts
