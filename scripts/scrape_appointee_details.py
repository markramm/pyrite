#!/usr/bin/env python3
"""
Scrape detailed financial disclosure data from ProPublica Trump Town.

Reads each appointee's detail page and extracts:
- Outside roles (Part 1)
- Employment assets (Part 3) — only high-value or conflict-relevant
- Employment agreements (Part 2)
- Compensation (Part 4)
- Spouse's assets (Part 5) — only high-value
- Other assets and income (Part 6) — only high-value
- Transactions (periodic reports) — all
- Liabilities (Part 8)

Updates person entries with summary data and creates linked entries for
significant holdings, roles, transactions, and liabilities.

Usage:
    # Scrape top 10 by priority
    python scripts/scrape_appointee_details.py --kb-path /path/to/kb --limit 10

    # Scrape specific person
    python scripts/scrape_appointee_details.py --kb-path /path/to/kb --person howard-lutnick

    # Dry run
    python scripts/scrape_appointee_details.py --kb-path /path/to/kb --limit 5 --dry-run

    # Set priority tags for cross-KB overlap
    python scripts/scrape_appointee_details.py --kb-path /path/to/kb --set-priorities
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# Priority 1: Cross-KB overlap (investigation KBs) + high net worth
PRIORITY_1 = {
    "howard-lutnick": "cascade-research, cascade-timeline, epstein-network, surveillance-industrial-complex",
    "stephen-andrew-feinberg": "cascade-timeline (Cerberus/DOD, Palantir Maven)",
    "gregory-j-barbaccia": "thiel-network, surveillance-industrial-complex (10yr Palantir, federal IT procurement)",
    "jacob-helberg": "thiel-network, surveillance-industrial-complex (Palantir advisor, State Dept)",
    "scott-bessent": "cascade-timeline (ethics violation, Argentina bailout)",
    "kash-patel": "cascade-research, surveillance-industrial-complex (PLTR stock, FBI Director)",
    "russell-vought": "cascade-research (Project 2025, OMB)",
    "stephen-n-miller": "surveillance-industrial-complex (PLTR stock, ICE policy)",
    "paul-atkins": "cascade-timeline (crypto conflicts, SEC)",
    "kelly-loeffler": "cascade-timeline (serial insider trading)",
    "charles-kushner": "cascade-research, cascade-timeline (Kushner network, Ambassador France)",
    "donald-j-trump": "cascade-timeline, cascade-research, epstein-network",
    "linda-mcmahon": "cascade-timeline (WWE abuse, Education dismantlement)",
    "todd-blanche": "epstein-network (Trump defense attorney, now DAG)",
    "clark-minor": "surveillance-industrial-complex (Palantir 11yr, HHS CTO)",
    "kevin-r-rhodes": "surveillance-industrial-complex (PLTR stock, federal procurement)",
    "troy-dean-edgar": "surveillance-industrial-complex (PLTR stock, DHS deputy)",
    "james-brendan-oneill": "thiel-network (Thiel Foundation CEO, HHS)",
    "michael-kratsios": "thiel-network (Thiel Capital, OSTP)",
}

# Priority 2: Cabinet + agency heads + billionaires without cross-KB overlap
PRIORITY_2_TAGS = {"cabinet", "billionaire", "centimillionaire"}

# Minimum value thresholds for creating holding entries
MIN_HOLDING_VALUE = 250_000  # $250K
MIN_HOLDING_VALUE_STR = "$250K"

# Conflict-relevant keywords (always create holding entries for these)
CONFLICT_KEYWORDS = [
    "palantir", "anduril", "clearview", "pltr", "meta", "google", "amazon",
    "lockheed", "raytheon", "boeing", "northrop", "general dynamics", "bae",
    "l3harris", "leidos", "saic", "booz allen", "peraton",
    "goldman sachs", "morgan stanley", "jpmorgan", "citigroup", "blackrock",
    "cerberus", "citadel", "bridgewater", "renaissance",
    "pfizer", "moderna", "johnson & johnson", "merck", "unitedhealth",
    "exxon", "chevron", "conocophillips", "halliburton",
    "bitcoin", "ethereum", "crypto", "coinbase", "tether",
    "geo group", "corecivic", "caliburn", "management & training",
    "tesla", "spacex", "starlink",
]

BASE_URL = "https://projects.propublica.org/trump-team-financial-disclosures/appointees"


def load_slug_mapping(kb_path: Path) -> dict[str, str]:
    """Load our-slug -> propublica-slug mapping."""
    mapping_file = kb_path / "slug-mapping.json"
    if mapping_file.exists():
        return json.loads(mapping_file.read_text())
    return {}


def parse_value_range(text: str) -> int:
    """Parse a value range string and return the midpoint in dollars."""
    text = text.strip()
    if not text or text == "None" or "less than" in text.lower():
        return 0

    # Remove "Value: " prefix
    text = re.sub(r"^Value:\s*", "", text)

    # Handle "$50M or more"
    if "or more" in text.lower():
        m = re.search(r"\$([\d,.]+)([BMK]?)", text)
        if m:
            return _parse_dollar(m.group(1), m.group(2))
        return 0

    # Handle ranges like "$1M - $5M"
    parts = re.findall(r"\$([\d,.]+)\s*([BMK]?)", text)
    if len(parts) == 2:
        low = _parse_dollar(parts[0][0], parts[0][1])
        high = _parse_dollar(parts[1][0], parts[1][1])
        return (low + high) // 2
    elif len(parts) == 1:
        return _parse_dollar(parts[0][0], parts[0][1])
    return 0


def _parse_dollar(num_str: str, suffix: str) -> int:
    """Parse '1.5' + 'M' -> 1500000."""
    num_str = num_str.replace(",", "")
    try:
        val = float(num_str)
    except ValueError:
        return 0
    multipliers = {"B": 1_000_000_000, "M": 1_000_000, "K": 1_000, "": 1}
    return int(val * multipliers.get(suffix, 1))


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    return s.strip("-")[:80]


def is_conflict_relevant(description: str) -> bool:
    """Check if a holding description matches conflict-relevant keywords."""
    desc_lower = description.lower()
    return any(kw in desc_lower for kw in CONFLICT_KEYWORDS)


def extract_tables(page) -> list[dict]:
    """Extract all data tables from an appointee detail page."""
    return page.evaluate("""() => {
        const tables = document.querySelectorAll('table');
        const result = [];
        tables.forEach((table, i) => {
            const headers = Array.from(table.querySelectorAll('th'))
                .map(th => th.textContent.trim());
            const rows = [];
            table.querySelectorAll('tbody tr').forEach(tr => {
                const cells = Array.from(tr.querySelectorAll('td'))
                    .map(td => td.textContent.trim());
                if (cells.length > 0 && cells.some(c => c)) {
                    rows.push(cells);
                }
            });
            result.push({index: i, headers: headers, rows: rows});
        });

        // Get asset range
        const text = document.querySelector('main')?.innerText || '';
        const rangeMatch = text.match(/Reported Asset Values\\n([^\\n]+)/);
        const assetRange = rangeMatch ? rangeMatch[1].trim() : '';

        // Get the section nav labels to map table indices
        const sectionLabels = [];
        const navLinks = document.querySelectorAll('a[href^="#"]');
        navLinks.forEach(a => {
            const t = a.textContent.trim();
            if (t && !t.includes('About') && !t.includes('Skip') &&
                !t.includes('Search') && !t.includes('What Is') &&
                !t.includes('How Did') && !t.includes('How Complete') &&
                t.length < 50) {
                sectionLabels.push(t);
            }
        });

        return {tables: result, assetRange: assetRange, sectionLabels: sectionLabels};
    }""")


def classify_tables(data: dict) -> dict:
    """Map tables to their disclosure sections based on headers."""
    sections = {}
    for table in data["tables"]:
        headers = tuple(h.lower() for h in table["headers"])
        idx = table["index"]

        if headers == ("organization", "position held", "endnote", "line no."):
            sections["outside_roles"] = table
        elif headers == ("organization", "agreement", "endnote", "line no."):
            sections["agreements"] = table
        elif headers == ("organization", "description", "endnote", "line no."):
            sections["compensation"] = table
        elif headers == ("creditor", "description", "endnote", "line no."):
            sections["liabilities"] = table
        elif headers == ("description", "value", "transaction", "endnote", "line no."):
            sections["transactions"] = table
        elif "description" in headers and "value" in headers and "income" in headers:
            # Multiple asset tables — assign by order
            if "employment_assets" not in sections:
                sections["employment_assets"] = table
            elif "spouse_assets" not in sections:
                sections["spouse_assets"] = table
            else:
                sections["other_assets"] = table

    sections["asset_range"] = data.get("assetRange", "")
    return sections


def extract_outside_roles(table: dict | None) -> list[dict]:
    """Extract outside roles from table data."""
    if not table:
        return []
    roles = []
    for row in table["rows"]:
        if len(row) < 2:
            continue
        org = row[0].strip()
        position_str = row[1].strip()
        if not org:
            continue

        # Parse "Director, 11/2010 - Present"
        is_current = "present" in position_str.lower()
        date_match = re.search(r"(\d{1,2}/\d{4})\s*-\s*(\w+|\d{1,2}/\d{4})", position_str)
        date_range = date_match.group(0) if date_match else ""
        position = re.sub(r",?\s*\d{1,2}/\d{4}\s*-\s*\S+", "", position_str).strip().rstrip(",")

        roles.append({
            "organization": org,
            "position": position,
            "date_range": date_range,
            "is_current": is_current,
        })
    return roles


def extract_holdings(table: dict | None, section_name: str) -> list[dict]:
    """Extract financial holdings, filtering for significance."""
    if not table:
        return []
    holdings = []
    for row in table["rows"]:
        if len(row) < 2:
            continue
        description = row[0].strip()
        value_str = row[1].strip() if len(row) > 1 else ""
        income_str = row[2].strip() if len(row) > 2 else ""
        income_type = row[3].strip() if len(row) > 3 else ""

        if not description:
            continue

        value = parse_value_range(value_str)
        is_significant = (
            value >= MIN_HOLDING_VALUE
            or is_conflict_relevant(description)
            or parse_value_range(income_str.replace("Income: ", "")) >= 100_000
        )

        if is_significant:
            holdings.append({
                "description": description,
                "value_range": value_str,
                "income_range": income_str,
                "income_type": income_type.replace("Income Type: ", ""),
                "section": section_name,
                "value_midpoint": value,
            })
    return holdings


def extract_transactions(table: dict | None) -> list[dict]:
    """Extract all transactions — they're all significant."""
    if not table:
        return []
    txns = []
    for row in table["rows"]:
        if len(row) < 3:
            continue
        description = row[0].strip()
        value_str = row[1].strip()
        txn_str = row[2].strip()

        if not description or not txn_str:
            continue

        # Parse "Transaction: Sale, 2025-08-12"
        txn_type = ""
        txn_date = ""
        m = re.match(r"Transaction:\s*(\w+),?\s*(\d{4}-\d{2}-\d{2})?", txn_str)
        if m:
            txn_type = m.group(1).lower()
            txn_date = m.group(2) or ""

        txns.append({
            "description": description,
            "value_range": value_str.replace("Value: ", ""),
            "transaction_type": txn_type,
            "date": txn_date,
        })
    return txns


def extract_liabilities(table: dict | None) -> list[dict]:
    """Extract liabilities."""
    if not table:
        return []
    liabilities = []
    for row in table["rows"]:
        if len(row) < 2:
            continue
        creditor = row[0].strip()
        desc = row[1].strip()
        if not creditor:
            continue

        # Parse "type: Capital Commitment, amount: $1,000,001 - $5,000,000, year-incurred: 2019, term: Life of Fund"
        liability_type = ""
        amount = ""
        year = ""
        term = ""
        rate = ""
        for part in desc.split(", "):
            part = part.strip()
            if part.startswith("type:"):
                liability_type = part[5:].strip()
            elif part.startswith("amount:"):
                amount = part[7:].strip()
            elif part.startswith("year-incurred:"):
                year = part[14:].strip()
            elif part.startswith("term:"):
                term = part[5:].strip()
            elif part.startswith("rate:"):
                rate = part[5:].strip()

        liabilities.append({
            "creditor": creditor,
            "liability_type": liability_type,
            "amount_range": amount,
            "year_incurred": year,
            "term": term,
            "rate": rate,
            "description": desc,
        })
    return liabilities


def extract_agreements(table: dict | None) -> list[dict]:
    """Extract employment agreements."""
    if not table:
        return []
    agreements = []
    for row in table["rows"]:
        if len(row) < 2:
            continue
        org = row[0].strip()
        agreement = row[1].strip()
        if not org:
            continue
        agreements.append({
            "organization": org,
            "description": agreement,
        })
    return agreements


def update_person_entry(person_path: Path, sections: dict, roles: list,
                        holdings: list, txns: list, liabilities: list,
                        agreements: list, cross_kb_refs: list | None = None,
                        propublica_url: str | None = None) -> str:
    """Update person markdown with enriched data."""
    text = person_path.read_text()
    parts = text.split("---")
    if len(parts) < 3:
        return text

    # Parse existing frontmatter
    fm_text = parts[1]

    # Add new fields to frontmatter — replace scrape_status if present
    fm_text = fm_text.replace("scrape_status: stub", "scrape_status: scraped")
    if "scrape_status:" not in fm_text:
        fm_text = fm_text.rstrip() + "\nscrape_status: scraped\n"

    additions = []
    if propublica_url and "propublica_url:" not in fm_text:
        additions.append(f'propublica_url: "{propublica_url}"')

    asset_range = sections.get("asset_range", "")
    if asset_range and "asset_range:" not in fm_text:
        additions.append(f'asset_range: "{asset_range}"')

    # Remove old count fields if re-scraping, then add fresh ones
    for field in ["outside_roles_count:", "holdings_count:", "agreements_count:",
                   "transactions_count:", "liabilities_count:", "asset_range:"]:
        lines = fm_text.split("\n")
        fm_text = "\n".join(l for l in lines if not l.strip().startswith(field))

    additions.append(f"outside_roles_count: {len(roles)}")
    additions.append(f"holdings_count: {sections.get('total_holdings', 0)}")
    additions.append(f"agreements_count: {len(agreements)}")
    additions.append(f"transactions_count: {len(txns)}")
    additions.append(f"liabilities_count: {len(liabilities)}")

    # Key holdings summary — only add if not already present
    if holdings and "key_holdings:" not in fm_text:
        top = sorted(holdings, key=lambda h: h["value_midpoint"], reverse=True)[:10]
        key_list = [f'- "{h["description"][:80]}"' for h in top]
        additions.append("key_holdings:\n" + "\n".join(key_list))

    # Cross-KB refs — only add if not already present
    if cross_kb_refs and "cross_kb_refs:" not in fm_text:
        ref_list = [f'- "{ref}"' for ref in cross_kb_refs]
        additions.append("cross_kb_refs:\n" + "\n".join(ref_list))

    # Insert before the closing ---
    new_fm = fm_text.rstrip() + "\n" + "\n".join(additions) + "\n"

    # Build enriched body
    body_parts = [parts[2].strip()]

    if roles:
        body_parts.append("\n## Outside Roles\n")
        current = [r for r in roles if r["is_current"]]
        former = [r for r in roles if not r["is_current"]]
        if current:
            body_parts.append(f"**{len(current)} current positions:**\n")
            for r in current[:20]:
                body_parts.append(f"- {r['position']} at {r['organization']} ({r['date_range']})")
        if former:
            body_parts.append(f"\n**{len(former)} former positions.**")

    if holdings:
        body_parts.append(f"\n## Notable Holdings ({len(holdings)} significant items)\n")
        for h in sorted(holdings, key=lambda x: x["value_midpoint"], reverse=True)[:15]:
            val = h["value_range"] or "undisclosed"
            body_parts.append(f"- **{h['description'][:100]}** — {val}")

    if txns:
        body_parts.append(f"\n## Transactions ({len(txns)} reported)\n")
        for t in txns:
            body_parts.append(f"- {t['transaction_type'].title()}: {t['description'][:80]} — {t['value_range']} ({t['date']})")

    if liabilities:
        body_parts.append(f"\n## Liabilities ({len(liabilities)} disclosed)\n")
        for li in liabilities[:10]:
            body_parts.append(f"- **{li['creditor']}** — {li['liability_type']}: {li['amount_range']}")

    new_body = "\n".join(body_parts) + "\n"

    return f"---{new_fm}---\n\n{new_body}"


def get_priority_list(kb_path: Path) -> list[tuple[str, int]]:
    """Build ordered list of (person_slug, priority) for scraping."""
    persons_dir = kb_path / "persons"
    priority_list = []

    for md_file in sorted(persons_dir.glob("*.md")):
        slug = md_file.stem
        text = md_file.read_text()

        # Skip already scraped
        if "scrape_status: scraped" in text or "scrape_status: enriched" in text:
            continue

        if slug in PRIORITY_1:
            priority_list.append((slug, 1))
        elif any(tag in text for tag in ["billionaire", "centimillionaire", "cabinet"]):
            priority_list.append((slug, 2))
        elif "ambassador" in text:
            priority_list.append((slug, 3))
        elif "decamillionaire" in text:
            priority_list.append((slug, 3))
        elif "millionaire" in text:
            priority_list.append((slug, 4))
        else:
            priority_list.append((slug, 5))

    # Sort by priority
    priority_list.sort(key=lambda x: x[1])
    return priority_list


def set_priorities(kb_path: Path):
    """Set scrape_priority and cross_kb_refs on person entries."""
    persons_dir = kb_path / "persons"
    updated = 0

    for md_file in sorted(persons_dir.glob("*.md")):
        slug = md_file.stem
        text = md_file.read_text()

        # Skip if already has priority
        if "scrape_priority:" in text:
            continue

        priority = 5
        refs = []

        if slug in PRIORITY_1:
            priority = 1
            refs_str = PRIORITY_1[slug]
        elif any(tag in text for tag in ["billionaire", "centimillionaire"]):
            priority = 2
        elif "cabinet" in text:
            priority = 2
        elif "ambassador" in text:
            priority = 3
        elif "decamillionaire" in text:
            priority = 3
        elif "millionaire" in text:
            priority = 4

        # Add priority to frontmatter
        if "scrape_status:" not in text:
            text = text.replace("status: confirmed", "status: confirmed\nscrape_status: stub")
        text = text.replace("scrape_status: stub",
                            f"scrape_status: stub\nscrape_priority: {priority}")

        if slug in PRIORITY_1:
            text = text.replace(
                f"scrape_priority: {priority}",
                f"scrape_priority: {priority}\ncross_kb_refs:\n- \"{PRIORITY_1[slug]}\""
            )

        md_file.write_text(text)
        updated += 1

    print(f"Set priorities on {updated} entries")

    # Count by priority
    counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for md_file in persons_dir.glob("*.md"):
        text = md_file.read_text()
        for p in range(1, 6):
            if f"scrape_priority: {p}" in text:
                counts[p] += 1
                break
    for p, c in sorted(counts.items()):
        print(f"  Priority {p}: {c} appointees")


def scrape_person(page, slug: str, kb_path: Path, slug_mapping: dict,
                   dry_run: bool = False) -> bool:
    """Scrape a single appointee's detail page and update their entry."""
    person_path = kb_path / "persons" / f"{slug}.md"
    if not person_path.exists():
        print(f"  SKIP {slug}: file not found")
        return False

    # Look up ProPublica URL slug
    pp_slug = slug_mapping.get(slug)
    if not pp_slug:
        print(f"  SKIP {slug}: no ProPublica URL mapping found")
        return False

    url = f"{BASE_URL}/{pp_slug}"
    print(f"  Scraping {slug} ({pp_slug})...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)  # Let JS render
    except Exception as e:
        print(f"  ERROR navigating to {slug}: {e}")
        return False

    try:
        data = extract_tables(page)
    except Exception as e:
        print(f"  ERROR extracting tables for {slug}: {e}")
        return False

    sections = classify_tables(data)
    roles = extract_outside_roles(sections.get("outside_roles"))
    emp_holdings = extract_holdings(sections.get("employment_assets"), "employment-assets")
    spouse_holdings = extract_holdings(sections.get("spouse_assets"), "spouse-assets")
    other_holdings = extract_holdings(sections.get("other_assets"), "other-assets")
    all_holdings = emp_holdings + spouse_holdings + other_holdings
    txns = extract_transactions(sections.get("transactions"))
    liabilities = extract_liabilities(sections.get("liabilities"))
    agreements = extract_agreements(sections.get("agreements"))

    # Count total holdings (not just significant ones)
    total = sum(
        len(sections.get(k, {}).get("rows", []))
        for k in ["employment_assets", "spouse_assets", "other_assets"]
        if isinstance(sections.get(k), dict)
    )
    sections["total_holdings"] = total

    cross_refs = None
    if slug in PRIORITY_1:
        cross_refs = [PRIORITY_1[slug]]

    if dry_run:
        print(f"  {slug}: {len(roles)} roles, {len(all_holdings)} significant holdings "
              f"(of {total}), {len(txns)} txns, {len(liabilities)} liabilities, "
              f"{len(agreements)} agreements, asset_range={sections.get('asset_range', '?')}")
        return True

    # Update person entry
    detail_url = f"{BASE_URL}/{pp_slug}"
    new_text = update_person_entry(
        person_path, sections, roles, all_holdings, txns, liabilities, agreements,
        cross_refs, propublica_url=detail_url
    )
    person_path.write_text(new_text)

    print(f"  {slug}: {len(roles)} roles, {len(all_holdings)} holdings, "
          f"{len(txns)} txns, {len(liabilities)} liabilities")
    return True


def main():
    parser = argparse.ArgumentParser(description="Scrape appointee financial disclosure details")
    parser.add_argument("--kb-path", required=True, help="Path to trump-appointee KB")
    parser.add_argument("--limit", type=int, default=10, help="Max appointees to scrape")
    parser.add_argument("--person", help="Scrape specific person by slug")
    parser.add_argument("--dry-run", action="store_true", help="Extract but don't write")
    parser.add_argument("--set-priorities", action="store_true", help="Set priority tags and exit")
    parser.add_argument("--min-priority", type=int, default=5, help="Only scrape up to this priority level")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds)")
    args = parser.parse_args()

    kb_path = Path(args.kb_path)
    if not kb_path.exists():
        print(f"KB path not found: {kb_path}")
        sys.exit(1)

    if args.set_priorities:
        set_priorities(kb_path)
        return

    # Build scrape list
    if args.person:
        scrape_list = [(args.person, 1)]
    else:
        scrape_list = get_priority_list(kb_path)
        scrape_list = [(s, p) for s, p in scrape_list if p <= args.min_priority]
        scrape_list = scrape_list[: args.limit]

    if not scrape_list:
        print("Nothing to scrape.")
        return

    # Load slug mapping
    slug_mapping = load_slug_mapping(kb_path)
    if not slug_mapping:
        print("ERROR: No slug-mapping.json found. Run initial extraction first.")
        sys.exit(1)

    # Filter out unmapped slugs
    mapped = [(s, p) for s, p in scrape_list if s in slug_mapping]
    unmapped = [(s, p) for s, p in scrape_list if s not in slug_mapping]
    if unmapped:
        print(f"WARNING: {len(unmapped)} appointees have no ProPublica URL mapping:")
        for s, p in unmapped[:10]:
            print(f"  {s} (priority {p})")
    scrape_list = mapped

    print(f"Scraping {len(scrape_list)} appointees (priorities {scrape_list[0][1]}-{scrape_list[-1][1]})")
    if args.dry_run:
        print("DRY RUN — no files will be modified\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Pyrite KB Builder; investigative journalism tool)"
        )
        page = context.new_page()

        success = 0
        failed = 0
        for slug, priority in scrape_list:
            if scrape_person(page, slug, kb_path, slug_mapping, dry_run=args.dry_run):
                success += 1
            else:
                failed += 1
            time.sleep(args.delay)

        browser.close()

    print(f"\nDone: {success} scraped, {failed} failed")
    if not args.dry_run:
        print(f"\nNext steps:")
        print(f"  pyrite index sync -k trump-appointees")


if __name__ == "__main__":
    main()
