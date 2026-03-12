"""Before-save hooks for journalism-investigation plugin."""

from typing import Any

from .utils import strip_wikilink


# ---------------------------------------------------------------------------
# Connection entry → auto-link mapping
# Maps (entry_type) → [(field_name, relation_on_field, relation_on_other)]
# e.g. ownership: owner field gets "owned_by" link (pointing at owner),
#                  asset field gets "owns" link (pointing at asset)
# ---------------------------------------------------------------------------

CONNECTION_LINK_SPECS: dict[str, list[tuple[str, str, str]]] = {
    "ownership": [
        ("owner", "owned_by", "owns"),
        ("asset", "owns", "owned_by"),
    ],
    "membership": [
        ("person", "has_member", "member_of"),
        ("organization", "member_of", "has_member"),
    ],
    "funding": [
        ("funder", "funded_by", "funds"),
        ("recipient", "funds", "funded_by"),
    ],
}


def enrich_connection_links(entry: Any, context: Any) -> Any:
    """Before-save hook: add bidirectional links for connection entry types."""
    entry_type = getattr(entry, "entry_type", "")
    specs = CONNECTION_LINK_SPECS.get(entry_type)
    if not specs:
        return entry

    # Collect existing link (target, relation) pairs to avoid duplicates
    existing = {(l.target, l.relation) for l in entry.links}

    for field_name, relation, _inverse in specs:
        ref = getattr(entry, field_name, "")
        if not ref:
            continue
        target_id = strip_wikilink(ref)
        if not target_id:
            continue
        if (target_id, relation) not in existing:
            entry.add_link(target=target_id, relation=relation)
            existing.add((target_id, relation))

    return entry
