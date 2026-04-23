#!/usr/bin/env python3
"""
Import Trump administration financial disclosures into a Pyrite KB.

Usage:
    python scripts/import_appointees.py data/appointees.txt --kb-path /path/to/kb

Input format (from ProPublica Trump Town financial disclosures):
    Name
    Position, Agency
    $Amount
    [blank line]
    ...

Generates one markdown entry per appointee with structured frontmatter.
"""

import argparse
import re
import sys
from pathlib import Path


def parse_amount(amount_str: str) -> tuple[str, int]:
    """Parse '$2B', '$791M', '$1.4M' etc. Return (display, cents)."""
    s = amount_str.strip().lstrip("$")
    multiplier = 1
    if s.endswith("B"):
        multiplier = 1_000_000_000
        s = s[:-1]
    elif s.endswith("M"):
        multiplier = 1_000_000
        s = s[:-1]
    elif s.endswith("K"):
        multiplier = 1_000
        s = s[:-1]

    try:
        value = int(float(s) * multiplier)
    except ValueError:
        value = 0

    return amount_str.strip(), value


def slugify(name: str) -> str:
    """Convert a name to a URL-friendly slug."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    return s.strip("-")


def extract_agency_short(agency: str) -> str:
    """Extract short agency name for tags."""
    mapping = {
        "Department of Defense": "dod",
        "White House": "white-house",
        "Department of State": "state",
        "Department of Commerce": "commerce",
        "Department of Health & Human Services": "hhs",
        "Department of the Treasury": "treasury",
        "Department of Justice": "justice",
        "Department of Energy": "energy",
        "Department of the Interior": "interior",
        "Department of Education": "education",
        "Department of Agriculture": "agriculture",
        "Department of Transportation": "transportation",
        "Department of Homeland Security": "dhs",
        "Department of Labor": "labor",
        "Department of Housing and Urban Development": "hud",
        "Department of Veterans Affairs": "va",
        "Environmental Protection Agency": "epa",
        "Office of Management and Budget": "omb",
        "Office of Personnel Management": "opm",
        "General Services Administration": "gsa",
        "Small Business Administration": "sba",
        "Securities and Exchange Commission": "sec",
        "Federal Communications Commission": "fcc",
        "National Aeronautics & Space Administration": "nasa",
        "Social Security Administration": "ssa",
        "Office of Science and Technology Policy": "ostp",
        "Office of the U.S. Trade Representative": "ustr",
    }
    for full, short in mapping.items():
        if full.lower() in agency.lower():
            return short
    return slugify(agency)[:20]


def wealth_tier(value: int) -> str:
    """Classify wealth tier for tags."""
    if value >= 1_000_000_000:
        return "billionaire"
    elif value >= 100_000_000:
        return "centimillionaire"
    elif value >= 10_000_000:
        return "decamillionaire"
    elif value >= 1_000_000:
        return "millionaire"
    return ""


def parse_appointees(text: str) -> list[dict]:
    """Parse the ProPublica appointee list format."""
    entries = []
    lines = text.strip().split("\n")
    i = 0

    while i < len(lines):
        # Skip blank lines
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break

        name = lines[i].strip()
        i += 1

        # Position line
        if i >= len(lines):
            break
        position_line = lines[i].strip()
        i += 1

        # Amount line
        if i >= len(lines):
            break
        amount_line = lines[i].strip()
        i += 1

        # Parse position and agency
        # Handle formats like "Secretary, Department of Commerce"
        # and "Deputy Secretary, Department of Defense"
        # Agency is usually the last "Department of X" or known org
        agency = ""
        position = position_line

        # Try to split on known agency patterns
        for pattern in [
            r",\s*(Department of .+)$",
            r",\s*(White House)$",
            r",\s*(Environmental Protection Agency)$",
            r",\s*(Office of .+)$",
            r",\s*(General Services Administration)$",
            r",\s*(Small Business Administration)$",
            r",\s*(Securities and Exchange Commission)$",
            r",\s*(Federal .+)$",
            r",\s*(National .+)$",
            r",\s*(Social Security Administration)$",
            r",\s*(Export-Import Bank)$",
            r",\s*(Nuclear Regulatory Commission)$",
            r",\s*(Consumer Product Safety Commission)$",
            r",\s*(Commodity Futures Trading Commission)$",
            r",\s*(Board of Governors .+)$",
            r",\s*(Central Intelligence Agency)$",
            r",\s*(U\.S\. .+)$",
            r",\s*(Surface Transportation Board)$",
            r",\s*(Pension Benefit Guaranty Corporation)$",
            r",\s*(National Credit Union Administration)$",
            r",\s*(Equal Employment Opportunity Commission)$",
            r",\s*(National Labor Relations Board)$",
            r",\s*(National Transportation Safety Board)$",
            r",\s*(Federal Deposit Insurance Corporation)$",
            r",\s*(Federal Maritime Commission)$",
        ]:
            m = re.search(pattern, position_line)
            if m:
                agency = m.group(1)
                position = position_line[: m.start()].strip().rstrip(",")
                break

        display_amount, value = parse_amount(amount_line)
        tier = wealth_tier(value)

        tags = ["trump-appointee", "financial-disclosure"]
        if tier:
            tags.append(tier)
        agency_tag = extract_agency_short(agency) if agency else ""
        if agency_tag:
            tags.append(agency_tag)

        # Determine if ambassador
        if "ambassador" in position.lower():
            tags.append("ambassador")
        if "secretary" in position.lower():
            tags.append("cabinet")

        entries.append({
            "name": name,
            "position": position,
            "agency": agency,
            "net_worth": display_amount,
            "net_worth_value": value,
            "slug": slugify(name),
            "tags": tags,
        })

    return entries


def yaml_quote(value: str) -> str:
    """Quote a string for YAML, using single quotes if it contains double quotes."""
    if '"' in value:
        return f"'{value}'"
    return f'"{value}"'


def generate_entry(appointee: dict, kb_name: str = "trump-appointees") -> str:
    """Generate a markdown entry for an appointee."""
    tags_yaml = "\n".join(f"- {t}" for t in appointee["tags"])

    return f"""---
id: {appointee['slug']}
type: person
title: {yaml_quote(appointee['name'])}
role: {yaml_quote(appointee['position'])}
affiliations:
- "{appointee['agency']}"
net_worth: "{appointee['net_worth']}"
importance: {min(10, max(5, 5 + len(str(appointee['net_worth_value'])) - 6))}
status: confirmed
tags:
{tags_yaml}
sources:
- title: "ProPublica Trump Town Financial Disclosure"
  url: "https://projects.propublica.org/trump-town/"
  outlet: ProPublica
  tier: 1
---

{appointee['name']} serves as {appointee['position']}{' at the ' + appointee['agency'] if appointee['agency'] else ''}. Disclosed net worth: {appointee['net_worth']}.
"""


def main():
    parser = argparse.ArgumentParser(description="Import appointee financial disclosures")
    parser.add_argument("input", help="Input text file with appointee data")
    parser.add_argument("--kb-path", required=True, help="Path to KB directory")
    parser.add_argument("--dry-run", action="store_true", help="Print entries without writing")
    args = parser.parse_args()

    text = Path(args.input).read_text()
    appointees = parse_appointees(text)
    print(f"Parsed {len(appointees)} appointees")

    kb_path = Path(args.kb_path)
    persons_dir = kb_path / "persons"

    if not args.dry_run:
        kb_path.mkdir(parents=True, exist_ok=True)
        persons_dir.mkdir(exist_ok=True)

        # Write kb.yaml if it doesn't exist
        kb_yaml = kb_path / "kb.yaml"
        if not kb_yaml.exists():
            kb_yaml.write_text(
                f"""name: trump-appointees
description: "Financial disclosures of Trump administration appointees — {len(appointees)} officials with disclosed assets"
kb_type: journalism-investigation
types:
  person:
    description: "An appointed official with financial disclosure data"
    subdirectory: persons
    required: [title]
    optional: [role, net_worth, affiliations]
"""
            )
            print(f"Created kb.yaml")

    for i, appointee in enumerate(appointees):
        md = generate_entry(appointee)
        filename = f"{appointee['slug']}.md"

        if args.dry_run:
            if i < 3:
                print(f"\n--- {filename} ---")
                print(md[:300])
            elif i == 3:
                print(f"\n... and {len(appointees) - 3} more")
        else:
            (persons_dir / filename).write_text(md)

    if not args.dry_run:
        print(f"Wrote {len(appointees)} entries to {persons_dir}")
        print(f"\nNext steps:")
        print(f"  pyrite kb add {kb_path} --name trump-appointees --type journalism-investigation")
        print(f"  pyrite index build")
    else:
        print(f"\nDry run complete. {len(appointees)} entries would be created.")


if __name__ == "__main__":
    main()
