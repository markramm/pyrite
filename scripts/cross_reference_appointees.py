#!/usr/bin/env python3
"""
Cross-reference trump-appointees with other investigation KBs.

For each priority 1-2 appointee, searches cascade-timeline, cascade-research,
thiel-network, epstein-network, surveillance-industrial-complex, and
detention-industrial for matching entries. Creates structured cross_kb_refs
in the person entry.

Usage:
    python scripts/cross_reference_appointees.py --kb-path /path/to/kb
    python scripts/cross_reference_appointees.py --kb-path /path/to/kb --person howard-lutnick
    python scripts/cross_reference_appointees.py --kb-path /path/to/kb --dry-run
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

INVESTIGATION_KBS = [
    "cascade-timeline",
    "cascade-research",
    "thiel-network",
    "epstein-network",
    "surveillance-industrial-complex",
    "detention-industrial",
]

PYRITE_CMD = ".venv/bin/pyrite"


def search_kb(query: str, kb_name: str, limit: int = 5) -> list[dict]:
    """Search a KB and return results."""
    try:
        result = subprocess.run(
            [PYRITE_CMD, "search", query, "-k", kb_name, "--limit", str(limit)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return data.get("results", [])
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
        return []


def extract_name(person_path: Path) -> str:
    """Extract the person's display name from frontmatter."""
    text = person_path.read_text()
    m = re.search(r'title:\s*["\'](.+?)["\']', text)
    return m.group(1) if m else person_path.stem.replace("-", " ").title()


def extract_last_name(name: str) -> str:
    """Extract likely last name for searching."""
    parts = name.split()
    # Skip common suffixes
    suffixes = {"jr.", "jr", "ii", "iii", "iv", "sr.", "sr"}
    for part in reversed(parts):
        if part.lower().strip(".") not in suffixes:
            return part
    return parts[-1] if parts else ""


def cross_reference_person(person_path: Path, dry_run: bool = False) -> dict:
    """Find cross-references for a person across investigation KBs."""
    text = person_path.read_text()
    name = extract_name(person_path)
    last_name = extract_last_name(name)
    slug = person_path.stem

    # Skip if not scraped
    if "scrape_status: scraped" not in text and "scrape_status: enriched" not in text:
        return {}

    refs = {}
    for kb in INVESTIGATION_KBS:
        results = search_kb(last_name, kb, limit=5)
        if results:
            # Filter for results that actually mention the person
            matching = []
            for r in results:
                snippet = r.get("snippet", "").lower()
                title = r.get("title", "").lower()
                # Check if the person's name appears in the result
                name_parts = name.lower().split()
                if (last_name.lower() in snippet or last_name.lower() in title
                        or any(p in snippet for p in name_parts if len(p) > 3)):
                    matching.append({
                        "id": r["id"],
                        "kb": kb,
                        "title": r.get("title", ""),
                        "snippet": r.get("snippet", "")[:150],
                    })
            if matching:
                refs[kb] = matching

    return refs


def update_person_refs(person_path: Path, refs: dict, dry_run: bool = False) -> int:
    """Update person entry with structured cross-KB references."""
    if not refs:
        return 0

    text = person_path.read_text()

    # Build structured refs
    ref_lines = []
    for kb, matches in refs.items():
        for m in matches[:3]:  # Max 3 per KB
            ref_lines.append(f'- "{kb}:{m["id"]}"')

    if not ref_lines:
        return 0

    if dry_run:
        name = extract_name(person_path)
        print(f"\n  {name}:")
        for kb, matches in refs.items():
            print(f"    {kb}: {len(matches)} matches")
            for m in matches[:2]:
                print(f"      - {m['title'][:80]}")
        return len(ref_lines)

    # Replace or add cross_kb_refs in frontmatter
    parts = text.split("---")
    if len(parts) < 3:
        return 0

    fm = parts[1]

    # Remove existing cross_kb_refs block
    lines = fm.split("\n")
    new_lines = []
    skip_list = False
    for line in lines:
        if line.strip().startswith("cross_kb_refs:"):
            skip_list = True
            continue
        if skip_list and line.strip().startswith("- "):
            continue
        skip_list = False
        new_lines.append(line)

    fm = "\n".join(new_lines)

    # Add new refs
    refs_yaml = "cross_kb_refs:\n" + "\n".join(ref_lines)
    fm = fm.rstrip() + "\n" + refs_yaml + "\n"

    person_path.write_text(f"---{fm}---{parts[2]}")
    return len(ref_lines)


def main():
    parser = argparse.ArgumentParser(description="Cross-reference appointees with investigation KBs")
    parser.add_argument("--kb-path", required=True, help="Path to trump-appointee KB")
    parser.add_argument("--person", help="Cross-reference specific person")
    parser.add_argument("--dry-run", action="store_true", help="Print refs without writing")
    parser.add_argument("--min-priority", type=int, default=2, help="Only process up to this priority")
    args = parser.parse_args()

    kb_path = Path(args.kb_path)
    persons_dir = kb_path / "persons"

    if args.person:
        path = persons_dir / f"{args.person}.md"
        if not path.exists():
            print(f"Not found: {path}")
            sys.exit(1)
        refs = cross_reference_person(path)
        n = update_person_refs(path, refs, args.dry_run)
        print(f"{args.person}: {n} cross-references")
        return

    total_refs = 0
    persons_with_refs = 0

    for md_file in sorted(persons_dir.glob("*.md")):
        text = md_file.read_text()

        # Filter by priority
        priority_match = re.search(r"scrape_priority: (\d)", text)
        if priority_match:
            priority = int(priority_match.group(1))
            if priority > args.min_priority:
                continue

        refs = cross_reference_person(md_file)
        if refs:
            n = update_person_refs(md_file, refs, args.dry_run)
            total_refs += n
            persons_with_refs += 1

    print(f"\nTotal: {persons_with_refs} appointees with cross-KB refs, {total_refs} references")
    if not args.dry_run and persons_with_refs > 0:
        print(f"\nNext: pyrite index sync -k trump-appointees")


if __name__ == "__main__":
    main()
