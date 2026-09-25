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
    # db.search takes raw FTS5: an unquoted hyphen ("smoke-test") parses as a
    # column filter and raises "no such column". Same sanitizer kb_search uses.
    from pyrite.services.search_service import SearchService

    query = SearchService.sanitize_fts_query(query)

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
        groups.append(
            {
                "kb_name": kb_name,
                "count": len(results),
                "results": results,
            }
        )

    total_count = sum(g["count"] for g in groups)

    return {
        "query": query,
        "total_count": total_count,
        "groups": groups,
    }


def correlate_results(
    flat_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Correlate results by entry ID first, then by normalized title.
    Matching IDs can identify the same entity even when its title differs
    between KBs. Results not grouped by ID fall back to case-insensitive title
    matching with repeated whitespace collapsed.
    """
    if not flat_results:
        return []

    def make_group(entries: list[dict[str, Any]], correlated_by: str) -> dict[str, Any]:
        title = entries[0].get("title", "")
        kb_names = {entry.get("kb_name", "") for entry in entries}
        max_importance = max(int(entry.get("importance", 5)) for entry in entries)
        appearances = [
            {
                "id": entry.get("id", ""),
                "kb_name": entry.get("kb_name", ""),
                "entry_type": entry.get("entry_type", ""),
                "importance": int(entry.get("importance", 5)),
            }
            for entry in entries
        ]
        return {
            "title": title,
            "correlated_by": correlated_by,
            "kb_count": len(kb_names),
            "max_importance": max_importance,
            "appearances": appearances,
        }

    by_id: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, result in enumerate(flat_results):
        entry_id = result.get("id")
        if entry_id is not None and str(entry_id).strip():
            by_id[str(entry_id)].append((index, result))
    groups = []
    grouped_indices: set[int] = set()
    for indexed_entries in by_id.values():
        if len(indexed_entries) < 2:
            continue
        groups.append(make_group([entry for _, entry in indexed_entries], "entry_id"))
        grouped_indices.update(index for index, _ in indexed_entries)
    by_title: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, result in enumerate(flat_results):
        if index in grouped_indices:
            continue
        title = str(result.get("title") or "")
        normalized_title = " ".join(title.split()).casefold()
        if normalized_title:
            by_title[normalized_title].append(result)
        else:
            # An empty title does not identify an entity; keep this result alone.
            groups.append(make_group([result], "title"))
    for entries in by_title.values():
        groups.append(make_group(entries, "title"))
    # Sort by KB appearance count descending, then importance descending.
    groups.sort(key=lambda group: (group["kb_count"], group["max_importance"]), reverse=True)
    return groups
