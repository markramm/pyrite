"""Beneficial ownership chain traversal and shell company detection.

Traces ownership chains through intermediaries to find beneficial owners,
computing effective ownership percentages and detecting shell companies.
"""

from typing import Any

from .utils import parse_meta, strip_wikilink


def _find_owners(all_ownership: list[dict[str, Any]], asset_id: str) -> list[dict[str, Any]]:
    """Find all ownership entries where the given entity is the asset."""
    results = []
    for entry in all_ownership:
        meta = parse_meta(entry)
        asset_ref = meta.get("asset", "")
        if strip_wikilink(asset_ref) == asset_id:
            pct_str = meta.get("percentage", "0")
            # Handle "51%" or "51" formats
            pct_str = pct_str.rstrip("%")
            try:
                pct = float(pct_str)
            except (ValueError, TypeError):
                pct = 0.0
            results.append({
                "owner_id": strip_wikilink(meta.get("owner", "")),
                "percentage": pct,
                "beneficial": bool(meta.get("beneficial", False)),
                "entry": entry,
            })
    return results


def _is_shell_company(
    entity_id: str,
    all_ownership: list[dict[str, Any]],
    all_membership: list[dict[str, Any]],
) -> bool:
    """Heuristic: entity is owner AND asset in ownership entries, but has no membership entries."""
    is_owner = False
    is_asset = False
    for entry in all_ownership:
        meta = parse_meta(entry)
        if strip_wikilink(meta.get("owner", "")) == entity_id:
            is_owner = True
        if strip_wikilink(meta.get("asset", "")) == entity_id:
            is_asset = True
        if is_owner and is_asset:
            break

    if not (is_owner and is_asset):
        return False

    # Check if any membership entry references this entity as the organization
    for entry in all_membership:
        meta = parse_meta(entry)
        org_ref = meta.get("organization", "")
        if strip_wikilink(org_ref) == entity_id:
            return False

    return True


def _trace_chains(
    all_ownership: list[dict[str, Any]],
    entity_id: str,
    max_depth: int,
    visited: set[str] | None = None,
    current_depth: int = 0,
) -> list[list[dict[str, Any]]]:
    """Recursively trace ownership chains upward from an entity.

    Returns a list of chains, where each chain is a list of path nodes
    (ordered from immediate owner to ultimate beneficial owner).
    """
    if current_depth >= max_depth:
        return []

    if visited is None:
        visited = set()

    owners = _find_owners(all_ownership, entity_id)
    if not owners:
        return []

    chains: list[list[dict[str, Any]]] = []
    for owner_info in owners:
        owner_id = owner_info["owner_id"]
        if not owner_id or owner_id in visited:
            # Circular reference or empty — treat as terminal
            chains.append([{
                "id": owner_id,
                "title": owner_id,
                "percentage": owner_info["percentage"],
                "beneficial": owner_info["beneficial"],
            }])
            continue

        node = {
            "id": owner_id,
            "title": owner_id,  # Will be enriched later
            "percentage": owner_info["percentage"],
            "beneficial": owner_info["beneficial"],
        }

        # Try to go further up the chain
        new_visited = visited | {entity_id}
        sub_chains = _trace_chains(
            all_ownership, owner_id, max_depth, new_visited, current_depth + 1
        )

        if sub_chains:
            for sub_chain in sub_chains:
                chains.append([node] + sub_chain)
        else:
            # This owner is terminal (beneficial owner)
            chains.append([node])

    return chains


def _enrich_titles(db, kb_name: str, chains: list[list[dict[str, Any]]]) -> None:
    """Replace ID-based titles with actual entry titles from DB."""
    # Collect all unique IDs
    all_ids = set()
    for chain in chains:
        for node in chain:
            all_ids.add(node["id"])

    # Fetch titles
    title_map: dict[str, str] = {}
    for eid in all_ids:
        entry = db.get_entry(eid, kb_name)
        if entry:
            title_map[eid] = entry.get("title", eid)

    # Update nodes
    for chain in chains:
        for node in chain:
            if node["id"] in title_map:
                node["title"] = title_map[node["id"]]


def trace_ownership_chain(
    db, kb_name: str, entity_id: str, max_depth: int = 5
) -> dict[str, Any]:
    """Trace ownership chains for an entity to find beneficial owners.

    Args:
        db: PyriteDB instance
        kb_name: Knowledge base name
        entity_id: ID of the entity to trace ownership for
        max_depth: Maximum chain depth to traverse (default 5)

    Returns:
        Dict with entity info, chains, beneficial_owners, and shell_indicators.
    """
    # Get entity info
    entity_entry = db.get_entry(entity_id, kb_name)
    entity_info = {
        "id": entity_id,
        "title": entity_entry.get("title", entity_id) if entity_entry else entity_id,
    }

    # Load all ownership entries for this KB
    all_ownership = db.list_entries(kb_name=kb_name, entry_type="ownership", limit=5000)

    # Trace chains
    raw_chains = _trace_chains(all_ownership, entity_id, max_depth)

    # Enrich titles
    _enrich_titles(db, kb_name, raw_chains)

    # Build chain results with effective percentages
    chains = []
    for path in raw_chains:
        effective = 100.0
        for node in path:
            effective *= node["percentage"] / 100.0
        chains.append({
            "path": path,
            "effective_percentage": effective,
        })

    # Identify beneficial owners (terminal nodes — end of each chain)
    beneficial_owners_map: dict[str, dict[str, Any]] = {}
    for chain in chains:
        if chain["path"]:
            terminal = chain["path"][-1]
            if terminal["id"] not in beneficial_owners_map:
                beneficial_owners_map[terminal["id"]] = {
                    "id": terminal["id"],
                    "title": terminal["title"],
                }

    beneficial_owners = list(beneficial_owners_map.values())

    # Shell company detection
    all_membership = db.list_entries(kb_name=kb_name, entry_type="membership", limit=5000)

    shell_indicators = []
    # Check intermediaries (all non-terminal nodes in any chain)
    intermediary_ids: set[str] = set()
    for chain in chains:
        for node in chain["path"][:-1]:  # All except terminal
            intermediary_ids.add(node["id"])

    for mid in intermediary_ids:
        if _is_shell_company(mid, all_ownership, all_membership):
            entry = db.get_entry(mid, kb_name)
            shell_indicators.append({
                "id": mid,
                "title": entry.get("title", mid) if entry else mid,
            })

    return {
        "entity": entity_info,
        "chains": chains,
        "beneficial_owners": beneficial_owners,
        "shell_indicators": shell_indicators,
    }


def aggregate_ownership(
    db, kb_name: str, entity_id: str
) -> dict[str, Any]:
    """Aggregate all beneficial owners and their effective ownership percentages.

    Args:
        db: PyriteDB instance
        kb_name: Knowledge base name
        entity_id: ID of the entity to aggregate ownership for

    Returns:
        Dict with entity info, aggregated beneficial_owners, and total_identified_ownership.
    """
    trace_result = trace_ownership_chain(db, kb_name, entity_id)

    # Aggregate by beneficial owner
    owner_agg: dict[str, dict[str, Any]] = {}
    for chain in trace_result["chains"]:
        if not chain["path"]:
            continue
        terminal = chain["path"][-1]
        bo_id = terminal["id"]
        if bo_id not in owner_agg:
            owner_agg[bo_id] = {
                "id": bo_id,
                "title": terminal["title"],
                "effective_percentage": 0.0,
                "via_chains": 0,
            }
        owner_agg[bo_id]["effective_percentage"] += chain["effective_percentage"]
        owner_agg[bo_id]["via_chains"] += 1

    beneficial_owners = sorted(
        owner_agg.values(), key=lambda x: x["effective_percentage"], reverse=True
    )

    total = sum(bo["effective_percentage"] for bo in beneficial_owners)

    return {
        "entity": trace_result["entity"],
        "beneficial_owners": beneficial_owners,
        "total_identified_ownership": total,
    }
