#!/usr/bin/env python3
"""
Auto-flag conflicts of interest in trump-appointees KB.

For each scraped person entry:
1. Get their agency
2. Scan holdings, outside roles, and liabilities against agency-specific conflict keywords
3. Write potential_conflicts list to frontmatter
4. Add conflict-flagged tag

Usage:
    python scripts/conflict_analysis.py --kb-path /path/to/kb
    python scripts/conflict_analysis.py --kb-path /path/to/kb --person howard-lutnick
    python scripts/conflict_analysis.py --kb-path /path/to/kb --dry-run
"""

import argparse
import re
import sys
from pathlib import Path

# Agency -> sectors/companies that create conflicts
AGENCY_CONFLICTS = {
    "Department of Defense": [
        "lockheed", "raytheon", "rtx", "boeing", "northrop grumman", "general dynamics",
        "bae systems", "l3harris", "leidos", "saic", "booz allen", "peraton",
        "palantir", "anduril", "shield ai", "cerberus", "dyncorp", "kbr",
        "defense", "military", "weapons", "munitions", "missile",
    ],
    "Department of Commerce": [
        "cantor fitzgerald", "bgc group", "newmark", "tether", "tariff",
        "trade", "export", "import", "semiconductor", "chip", "intel", "tsmc",
        "huawei", "tiktok", "bytedance",
    ],
    "Securities and Exchange Commission": [
        "crypto", "bitcoin", "ethereum", "coinbase", "binance", "tether",
        "securities", "exchange", "broker", "dealer", "hedge fund",
        "goldman sachs", "morgan stanley", "jpmorgan", "citigroup",
        "blackrock", "citadel", "bridgewater", "renaissance",
    ],
    "Department of the Treasury": [
        "goldman sachs", "morgan stanley", "jpmorgan", "citigroup", "bank of america",
        "wells fargo", "blackrock", "blackstone", "hedge fund", "private equity",
        "banking", "financial", "currency", "forex", "bond",
    ],
    "Department of Homeland Security": [
        "palantir", "geo group", "corecivic", "caliburn", "management & training",
        "clearview", "surveillance", "biometric", "ice", "customs",
        "border", "detention", "immigration", "bi incorporated",
    ],
    "Department of Health & Human Services": [
        "pfizer", "moderna", "johnson & johnson", "merck", "unitedhealth",
        "abbvie", "eli lilly", "amgen", "gilead", "bristol-myers",
        "pharmaceutical", "pharma", "vaccine", "drug", "insurance", "health",
    ],
    "Department of Energy": [
        "exxon", "chevron", "conocophillips", "halliburton", "schlumberger",
        "bp", "shell", "oil", "gas", "petroleum", "nuclear", "solar", "wind",
        "energy", "fossil fuel", "lng", "pipeline",
    ],
    "Environmental Protection Agency": [
        "exxon", "chevron", "dow chemical", "dupont", "3m", "monsanto",
        "pollution", "emission", "coal", "oil", "gas", "chemical",
        "pesticide", "contamination",
    ],
    "Department of Education": [
        "student loan", "sallie mae", "navient", "charter school",
        "education management", "textbook", "pearson", "mcgraw-hill",
    ],
    "Department of State": [
        "arms", "defense export", "foreign agent", "embassy",
        "diplomatic", "sanctions",
    ],
    "Department of Justice": [
        "law firm", "legal", "prison", "corrections", "geo group", "corecivic",
        "palantir", "surveillance", "crypto", "blockchain",
    ],
    "Department of the Interior": [
        "oil", "gas", "mining", "drilling", "extraction", "timber", "grazing",
        "coal", "public land", "national park",
    ],
    "Department of Agriculture": [
        "monsanto", "bayer", "syngenta", "cargill", "adm", "tyson",
        "farming", "agribusiness", "pesticide", "subsidy",
    ],
    "Department of Transportation": [
        "airline", "railroad", "auto", "trucking", "shipping",
        "boeing", "airbus", "tesla", "uber", "lyft",
    ],
    "Department of Housing and Urban Development": [
        "real estate", "mortgage", "housing", "fannie mae", "freddie mac",
        "construction", "developer", "landlord",
    ],
    "Department of Labor": [
        "union", "labor", "employment", "staffing", "temp agency",
        "wage", "worker",
    ],
    "Department of Veterans Affairs": [
        "hospital", "medical", "healthcare", "pharmaceutical",
        "disability", "veteran",
    ],
    "Small Business Administration": [
        "lending", "loan", "small business", "venture",
    ],
    "Office of Management and Budget": [
        "contractor", "procurement", "federal contract",
        "palantir", "anduril", "leidos", "booz allen",
    ],
    "Office of Personnel Management": [
        "staffing", "hr", "human resources", "benefits",
        "retirement", "pension",
    ],
    "White House": [
        # White House officials could conflict with anything
        "palantir", "tesla", "spacex", "crypto", "bitcoin",
    ],
    "National Aeronautics & Space Administration": [
        "spacex", "blue origin", "boeing", "lockheed", "northrop",
        "raytheon", "rocket", "satellite", "launch",
    ],
    "Social Security Administration": [
        "insurance", "disability", "retirement", "pension",
        "financial services",
    ],
    "Federal Trade Commission": [
        "meta", "google", "amazon", "apple", "microsoft",
        "antitrust", "merger", "acquisition", "monopoly",
    ],
    "Federal Communications Commission": [
        "telecom", "comcast", "at&t", "verizon", "t-mobile",
        "spectrum", "broadcast", "media", "5g",
    ],
}

# Universal conflict keywords (apply to all agencies)
UNIVERSAL_CONFLICTS = [
    "palantir", "tesla", "spacex", "meta", "google", "amazon",
    "goldman sachs", "morgan stanley", "jpmorgan",
    "bitcoin", "crypto", "ethereum",
]


def find_conflicts(agency: str, body_text: str, holdings_text: str) -> list[str]:
    """Find potential conflicts between agency and holdings/roles."""
    conflicts = []
    body_lower = body_text.lower()
    holdings_lower = holdings_text.lower()
    combined = body_lower + " " + holdings_lower

    # Get agency-specific keywords
    keywords = []
    for agency_name, kws in AGENCY_CONFLICTS.items():
        if agency_name.lower() in agency.lower() or agency.lower() in agency_name.lower():
            keywords = kws
            break

    # Add universal conflicts
    all_keywords = list(set(keywords + UNIVERSAL_CONFLICTS))

    for kw in all_keywords:
        if kw in combined:
            # Find the context — which holding/role mentions this
            # Search in the body for a line containing the keyword
            for line in body_text.split("\n"):
                if kw.lower() in line.lower() and line.strip().startswith("- "):
                    # Extract the holding/role description
                    desc = line.strip("- *").strip()
                    if len(desc) > 20:  # Skip noise
                        conflict_desc = f"Holds/role: {desc[:120]} (conflict with {agency})"
                        if conflict_desc not in conflicts:
                            conflicts.append(conflict_desc)
                        break

    return conflicts[:10]  # Cap at 10


def analyze_person(person_path: Path, dry_run: bool = False) -> int:
    """Analyze a single person entry for conflicts. Returns count of conflicts found."""
    text = person_path.read_text()

    # Only analyze scraped entries
    if "scrape_status: scraped" not in text and "scrape_status: enriched" not in text:
        return 0

    # Skip if already has conflicts
    if "potential_conflicts:" in text:
        return 0

    # Extract agency from frontmatter
    agency_match = re.search(r'^affiliations:\n- "(.+?)"', text, re.MULTILINE)
    if not agency_match:
        return 0
    agency = agency_match.group(1)

    # Split into frontmatter and body
    parts = text.split("---")
    if len(parts) < 3:
        return 0
    fm = parts[1]
    body = parts[2]

    # Also extract key_holdings from frontmatter
    holdings_section = ""
    in_holdings = False
    for line in fm.split("\n"):
        if line.strip().startswith("key_holdings:"):
            in_holdings = True
            continue
        if in_holdings:
            if line.strip().startswith("- "):
                holdings_section += line + "\n"
            else:
                in_holdings = False

    conflicts = find_conflicts(agency, body, holdings_section)

    if not conflicts:
        return 0

    if dry_run:
        print(f"  {person_path.stem}: {len(conflicts)} conflicts")
        for c in conflicts[:3]:
            print(f"    - {c[:100]}")
        return len(conflicts)

    # Add conflicts to frontmatter
    conflicts_yaml = "potential_conflicts:\n" + "\n".join(
        f'- "{c}"' for c in conflicts
    )

    # Add conflict-flagged tag
    if "conflict-flagged" not in text:
        text = text.replace("tags:\n", "tags:\n- conflict-flagged\n", 1)

    # Insert before closing ---
    # Find the second --- (end of frontmatter)
    first_end = text.index("---", 3) + 3
    fm_section = text[3:first_end - 3]
    rest = text[first_end:]

    new_fm = fm_section.rstrip() + "\n" + conflicts_yaml + "\n"
    person_path.write_text(f"---{new_fm}---{rest}")

    return len(conflicts)


def main():
    parser = argparse.ArgumentParser(description="Analyze appointee conflicts of interest")
    parser.add_argument("--kb-path", required=True, help="Path to trump-appointee KB")
    parser.add_argument("--person", help="Analyze specific person")
    parser.add_argument("--dry-run", action="store_true", help="Print conflicts without writing")
    args = parser.parse_args()

    kb_path = Path(args.kb_path)
    persons_dir = kb_path / "persons"

    if args.person:
        path = persons_dir / f"{args.person}.md"
        if not path.exists():
            print(f"Not found: {path}")
            sys.exit(1)
        n = analyze_person(path, args.dry_run)
        print(f"{args.person}: {n} conflicts")
        return

    total_conflicts = 0
    persons_with_conflicts = 0

    for md_file in sorted(persons_dir.glob("*.md")):
        n = analyze_person(md_file, args.dry_run)
        if n > 0:
            total_conflicts += n
            persons_with_conflicts += 1

    print(f"\nTotal: {persons_with_conflicts} appointees with conflicts, {total_conflicts} conflict flags")
    if not args.dry_run and persons_with_conflicts > 0:
        print(f"\nNext: pyrite index sync -k trump-appointees")


if __name__ == "__main__":
    main()
