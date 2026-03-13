"""Unified cross-KB search with result correlation.

Searches across multiple KBs and groups results both by KB
and by entity identity (title matching).
"""

from collections import defaultdict
from typing import Any


def cross_kb_search(
    db: Any,
    query: str,
    *,
    kb_names: list[str] | None = None,
    entry_type: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Search across multiple KBs, returning results grouped by KB.

    Args:
        db: PyriteDB instance
        query: Search query string
        kb_names: Specific KBs to search (None = all KBs)
        entry_type: Filter by entry type
        limit: Max total results

    Returns:
        Dict with query, total_count, and groups (list of {kb_name, count, results})
    """
    if kb_names:
        # Search each specified KB separately and combine
        all_results: list[dict[str, Any]] = []
        for kb_name in kb_names:
            results = db.search(
                query,
                kb_name=kb_name,
                entry_type=entry_type,
                limit=limit,
            )
            all_results.extend(results)
    else:
        # Search all KBs at once
        all_results = db.search(
            query,
            kb_name=None,
            entry_type=entry_type,
            limit=limit,
        )

    # Group by KB
    by_kb: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in all_results:
        by_kb[r.get("kb_name", "unknown")].append(r)

    groups = []
    for kb_name, results in sorted(by_kb.items()):
        groups.append({
            "kb_name": kb_name,
            "count": len(results),
            "results": results,
        })

    total_count = sum(g["count"] for g in groups)

    return {
        "query": query,
        "total_count": total_count,
        "groups": groups,
    }


def correlate_results(
    flat_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Correlate search results by entity identity across KBs.

    Groups results with matching titles (case-insensitive) and
    sorts by cross-KB appearance count (entities in more KBs rank higher).

    Args:
        flat_results: List of search result dicts with id, kb_name, title, entry_type

    Returns:
        List of entity groups, each with title, kb_count, max_importance, appearances
    """
    if not flat_results:
        return []

    # Group by normalized title
    by_title: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in flat_results:
        key = r.get("title", "").strip().lower()
        by_title[key].append(r)

    groups = []
    for title_key, entries in by_title.items():
        # Use the original-case title from the first entry
        title = entries[0].get("title", "")
        kb_names = {e.get("kb_name", "") for e in entries}
        max_importance = max(int(e.get("importance", 5)) for e in entries)

        appearances = []
        for e in entries:
            appearances.append({
                "id": e.get("id", ""),
                "kb_name": e.get("kb_name", ""),
                "entry_type": e.get("entry_type", ""),
                "importance": int(e.get("importance", 5)),
            })

        groups.append({
            "title": title,
            "kb_count": len(kb_names),
            "max_importance": max_importance,
            "appearances": appearances,
        })

    # Sort by kb_count descending, then by max_importance descending
    groups.sort(key=lambda g: (g["kb_count"], g["max_importance"]), reverse=True)

    return groups
