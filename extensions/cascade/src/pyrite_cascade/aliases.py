"""Actor alias suggestion and fuzzy matching.

Ported from kleptocracy-timeline/scripts/maintenance/suggest_actor_aliases.py.
Multi-pass duplicate detection pipeline that proposes alias groups for actor
names found across events in a Cascade KB.
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

# ── Known acronym table ─────────────────────────────────────────────────────

KNOWN_ACRONYMS: dict[str, str] = {
    "FBI": "Federal Bureau of Investigation",
    "CIA": "Central Intelligence Agency",
    "NSA": "National Security Agency",
    "DOJ": "Department of Justice",
    "DOD": "Department of Defense",
    "DHS": "Department of Homeland Security",
    "EPA": "Environmental Protection Agency",
    "SEC": "Securities and Exchange Commission",
    "FCC": "Federal Communications Commission",
    "FTC": "Federal Trade Commission",
    "FDA": "Food and Drug Administration",
    "IRS": "Internal Revenue Service",
    "ICE": "Immigration and Customs Enforcement",
    "CBP": "Customs and Border Protection",
    "ATF": "Bureau of Alcohol, Tobacco, Firearms and Explosives",
    "DEA": "Drug Enforcement Administration",
    "FEMA": "Federal Emergency Management Agency",
    "NASA": "National Aeronautics and Space Administration",
    "USPS": "United States Postal Service",
    "GAO": "Government Accountability Office",
    "CBO": "Congressional Budget Office",
    "OMB": "Office of Management and Budget",
    "OPM": "Office of Personnel Management",
    "GSA": "General Services Administration",
    "CFPB": "Consumer Financial Protection Bureau",
    "NLRB": "National Labor Relations Board",
    "OSHA": "Occupational Safety and Health Administration",
    "HHS": "Department of Health and Human Services",
    "HUD": "Department of Housing and Urban Development",
    "USDA": "United States Department of Agriculture",
    "DOE": "Department of Energy",
    "DOI": "Department of the Interior",
    "DOT": "Department of Transportation",
    "VA": "Department of Veterans Affairs",
    "DOGE": "Department of Government Efficiency",
    "USAID": "United States Agency for International Development",
    "NATO": "North Atlantic Treaty Organization",
    "UN": "United Nations",
    "WHO": "World Health Organization",
    "IMF": "International Monetary Fund",
    "SCOTUS": "Supreme Court of the United States",
    "ACLU": "American Civil Liberties Union",
    "NRA": "National Rifle Association",
    "GOP": "Republican Party",
    "DNC": "Democratic National Committee",
    "RNC": "Republican National Committee",
    "PAC": "Political Action Committee",
    "NAACP": "National Association for the Advancement of Colored People",
}


# ── Proposal data structure ─────────────────────────────────────────────────

@dataclass
class AliasProposal:
    """A proposed alias grouping with confidence score."""

    canonical: str
    aliases: list[str]
    strategy: str
    confidence: int
    counts: dict[str, int] = field(default_factory=dict, repr=False)

    @property
    def total_uses(self) -> int:
        return sum(self.counts.get(n, 0) for n in [self.canonical] + self.aliases)

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical": self.canonical,
            "aliases": self.aliases,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "total_uses": self.total_uses,
        }


# ── Normalization helpers ────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert text to a slug for comparison."""
    text = unicodedata.normalize("NFKD", text)
    # Remove combining characters (accents, cedillas, etc.)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"[''`]s\b", "s", text)  # possessives
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


def strip_prefix(name: str) -> str | None:
    """Remove U.S./US/United States prefix."""
    for prefix in ["U.S. ", "US ", "United States "]:
        if name.startswith(prefix):
            return name[len(prefix):]
    return None


def strip_parenthetical(name: str) -> tuple[str | None, str | None]:
    """Remove parenthetical from name, return (base, acronym_or_none)."""
    m = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", name)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None


# ── Canonical name selection ─────────────────────────────────────────────────

def pick_canonical(names: list[str], counts: dict[str, int]) -> str:
    """Choose the canonical name from a set of candidates.

    Priority: full name > no prefix > proper case > no parenthetical > highest count.
    """
    def score(name: str) -> tuple:
        is_acronym = name.isupper() and len(name) <= 8
        has_prefix = any(name.startswith(p) for p in ["U.S. ", "US ", "United States "])
        has_paren = "(" in name
        is_proper = name[0].isupper() if name else False

        prefix_dominant = False
        if has_prefix:
            total = sum(counts.get(n, 0) for n in names)
            if total > 0 and counts.get(name, 0) / total >= 0.8:
                prefix_dominant = True

        return (
            0 if is_acronym else 1,            # prefer full name
            0 if (has_prefix and not prefix_dominant) else 1,  # prefer no prefix
            1 if is_proper else 0,              # prefer proper case
            0 if has_paren else 1,              # prefer no parenthetical
            counts.get(name, 0),                # highest count breaks ties
        )

    return max(names, key=score)


# ── Detection strategies ─────────────────────────────────────────────────────

def find_case_duplicates(
    actors: list[str], counts: dict[str, int],
) -> tuple[list[AliasProposal], set[str]]:
    """Pass 1: Exact case-insensitive matches."""
    lower_groups: dict[str, list[str]] = defaultdict(list)
    for actor in actors:
        lower_groups[actor.lower()].append(actor)

    proposals = []
    matched: set[str] = set()
    for group in lower_groups.values():
        if len(group) < 2:
            continue
        canonical = pick_canonical(group, counts)
        aliases = [a for a in group if a != canonical]
        proposals.append(AliasProposal(canonical, aliases, "exact-case", 100, counts))
        matched.update(group)
    return proposals, matched


def find_slug_duplicates(
    actors: list[str], counts: dict[str, int],
) -> tuple[list[AliasProposal], set[str]]:
    """Pass 2: Group actors with identical slugs."""
    slug_groups: dict[str, list[str]] = defaultdict(list)
    for actor in actors:
        slug_groups[slugify(actor)].append(actor)

    proposals = []
    matched: set[str] = set()
    for group in slug_groups.values():
        if len(group) < 2:
            continue
        canonical = pick_canonical(group, counts)
        aliases = [a for a in group if a != canonical]
        proposals.append(AliasProposal(canonical, aliases, "slug-match", 95, counts))
        matched.update(group)
    return proposals, matched


def find_prefix_duplicates(
    actors: list[str], counts: dict[str, int],
) -> tuple[list[AliasProposal], set[str]]:
    """Pass 3: U.S./US prefix stripping."""
    actor_set = set(actors)
    proposals = []
    matched: set[str] = set()

    for actor in actors:
        stripped = strip_prefix(actor)
        if stripped and stripped in actor_set and stripped not in matched and actor not in matched:
            group = [actor, stripped]
            canonical = pick_canonical(group, counts)
            aliases = [a for a in group if a != canonical]
            proposals.append(AliasProposal(canonical, aliases, "prefix-strip", 90, counts))
            matched.update(group)
    return proposals, matched


def find_parenthetical_duplicates(
    actors: list[str], counts: dict[str, int],
) -> tuple[list[AliasProposal], set[str]]:
    """Pass 4: Parenthetical removal (+ acronym matching)."""
    actor_set = set(actors)
    proposals = []
    matched: set[str] = set()

    for actor in actors:
        base, acronym = strip_parenthetical(actor)
        if base is None:
            continue

        group = {actor}
        if base in actor_set:
            group.add(base)
        if acronym and acronym in actor_set:
            group.add(acronym)

        if len(group) < 2 or group & matched:
            continue

        canonical = pick_canonical(list(group), counts)
        aliases = sorted(a for a in group if a != canonical)
        proposals.append(AliasProposal(canonical, aliases, "parenthetical", 90, counts))
        matched.update(group)
    return proposals, matched


def find_acronym_duplicates(
    actors: list[str], counts: dict[str, int],
) -> tuple[list[AliasProposal], set[str]]:
    """Pass 5: Known acronym table matching."""
    actor_set = set(actors)
    full_to_acronym = {v: k for k, v in KNOWN_ACRONYMS.items()}
    proposals = []
    matched: set[str] = set()

    for actor in actors:
        if actor in matched:
            continue

        group = {actor}

        if actor in KNOWN_ACRONYMS:
            full = KNOWN_ACRONYMS[actor]
            if full in actor_set:
                group.add(full)
            for prefix in ["U.S. ", "US "]:
                prefixed = prefix + full
                if prefixed in actor_set:
                    group.add(prefixed)

        if actor in full_to_acronym:
            acr = full_to_acronym[actor]
            if acr in actor_set:
                group.add(acr)

        if len(group) < 2 or group & matched:
            continue

        canonical = pick_canonical(list(group), counts)
        aliases = sorted(a for a in group if a != canonical)
        proposals.append(AliasProposal(canonical, aliases, "known-acronym", 85, counts))
        matched.update(group)
    return proposals, matched


def find_fuzzy_duplicates(
    actors: list[str], counts: dict[str, int],
    threshold: float = 0.85, min_count: int = 2,
) -> tuple[list[AliasProposal], set[str]]:
    """Pass 6: Fuzzy matching using difflib, grouped by first word."""
    candidates = [a for a in actors if counts.get(a, 0) >= min_count]

    first_word_groups: dict[str, list[str]] = defaultdict(list)
    for actor in candidates:
        first = actor.split()[0].lower() if actor.split() else ""
        first_word_groups[first].append(actor)

    proposals = []
    matched: set[str] = set()

    for group in first_word_groups.values():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a in matched or b in matched:
                    continue
                ratio = SequenceMatcher(None, a.lower(), b.lower()).ratio()
                if ratio >= threshold:
                    pair = [a, b]
                    canonical = pick_canonical(pair, counts)
                    aliases = [x for x in pair if x != canonical]
                    confidence = int(ratio * 100)
                    proposals.append(AliasProposal(canonical, aliases, "fuzzy", confidence, counts))
                    matched.update(pair)
    return proposals, matched


# ── Main pipeline ────────────────────────────────────────────────────────────

def run_detection(actor_counts: dict[str, int]) -> list[AliasProposal]:
    """Run all detection strategies in order, each pass removes matched actors."""
    remaining = set(actor_counts.keys())
    all_proposals: list[AliasProposal] = []

    strategies = [
        find_case_duplicates,
        find_slug_duplicates,
        find_prefix_duplicates,
        find_parenthetical_duplicates,
        find_acronym_duplicates,
        find_fuzzy_duplicates,
    ]

    for fn in strategies:
        proposals, matched = fn(list(remaining), actor_counts)
        all_proposals.extend(proposals)
        remaining -= matched

    all_proposals.sort(key=lambda p: (-p.confidence, -p.total_uses))
    return all_proposals


# ── Actor extraction from Pyrite DB ──────────────────────────────────────────

def extract_actor_counts_from_db(
    db: Any, kb_name: str, event_types: list[str] | None = None,
) -> Counter:
    """Extract actor name → count mapping from events in a Pyrite KB."""
    if event_types is None:
        event_types = ["timeline_event", "solidarity_event", "scene"]

    actor_counts: Counter = Counter()
    for etype in event_types:
        results = db.list_entries(kb_name=kb_name, entry_type=etype, limit=10000)
        for r in results:
            meta = r.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = {}
            for actor in meta.get("actors") or []:
                if actor and isinstance(actor, str):
                    actor_counts[actor] += 1
    return actor_counts


def extract_actor_counts_from_alias_file(alias_file: Path) -> dict[str, list[str]]:
    """Load an existing actor_aliases.json file."""
    if not alias_file.exists():
        return {}
    with open(alias_file) as f:
        return json.load(f)


def apply_proposals(
    proposals: list[AliasProposal],
    min_confidence: int = 0,
) -> dict[str, list[str]]:
    """Convert accepted proposals to a canonical → aliases dict.

    Auto-accepts proposals at or above min_confidence, skipping conflicts.
    """
    accepted: dict[str, list[str]] = {}
    used_names: set[str] = set()

    for p in proposals:
        if p.confidence < min_confidence:
            continue
        all_names = {p.canonical} | set(p.aliases)
        if all_names & used_names:
            continue
        accepted[p.canonical] = sorted(p.aliases)
        used_names.update(all_names)

    return dict(sorted(accepted.items()))
