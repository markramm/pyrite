"""Unified cross-KB search with result correlation.

Searches across multiple KBs and groups results by KB
and by entity identity using entry IDs and normalized title matches.
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
    """Correlate results transitively by entry ID or normalized title.

    A result can connect an ID-matched result to another result that matches
    by title, so both keys participate in the same equivalence groups.
    """
    if not flat_results:
        return []

    def make_group(entries: list[dict[str, Any]], correlated_by: str) -> dict[str, Any]:
        title = entries[0].get("title") or ""
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

    parents = list(range(len(flat_results)))
    ranks = [0] * len(flat_results)

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(first: int, second: int) -> None:
        first_root = find(first)
        second_root = find(second)
        if first_root == second_root:
            return
        if ranks[first_root] < ranks[second_root]:
            first_root, second_root = second_root, first_root
        parents[second_root] = first_root
        if ranks[first_root] == ranks[second_root]:
            ranks[first_root] += 1

    by_id: dict[str, list[int]] = defaultdict(list)
    by_title: dict[str, list[int]] = defaultdict(list)
    for index, result in enumerate(flat_results):
        entry_id = result.get("id")
        normalized_id = str(entry_id).strip() if entry_id is not None else ""
        if normalized_id:
            by_id[normalized_id].append(index)
        title = str(result.get("title") or "")
        normalized_title = " ".join(title.split()).casefold()
        if normalized_title:
            by_title[normalized_title].append(index)

    for key_groups in (by_id.values(), by_title.values()):
        for indexes in key_groups:
            for index in indexes[1:]:
                union(indexes[0], index)

    id_linked_roots = {find(indexes[0]) for indexes in by_id.values() if len(indexes) > 1}
    components: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for index, result in enumerate(flat_results):
        components[find(index)].append(result)

    groups = [
        make_group(entries, "entry_id" if root in id_linked_roots else "title")
        for root, entries in components.items()
    ]
    # Sort by KB appearance count descending, then importance descending.
    groups.sort(key=lambda group: (group["kb_count"], group["max_importance"]), reverse=True)
    return groups
