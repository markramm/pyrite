"""Investigation guided setup and status reporting.

Provides functions for:
- Creating new investigations with initial entities and questions
- Building comprehensive status reports for context rebuild
"""

from typing import Any

from pyrite.schema import generate_entry_id

from .queries import ENTITY_TYPE_ALIASES, query_claims, query_entities, query_sources, query_timeline
from .utils import parse_meta


def create_investigation(
    db: Any,
    kb_name: str,
    title: str,
    scope: str = "",
    key_questions: list[str] | None = None,
    initial_entities: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Create a new investigation with optional initial entities.

    Args:
        db: PyriteDB instance
        kb_name: Target KB name
        title: Investigation title
        scope: Description of investigation scope
        key_questions: List of key questions to investigate
        initial_entities: List of {"name": ..., "type": ...} dicts for initial entities

    Returns:
        Dict with created investigation ID and any created entities
    """
    if not title.strip():
        return {"error": "Investigation title is required"}

    entry_id = generate_entry_id(title)

    # Build body from scope and key questions
    body_parts = []
    if scope:
        body_parts.append(scope)
    if key_questions:
        body_parts.append("\n## Key Questions\n")
        for q in key_questions:
            body_parts.append(f"- {q}")

    body = "\n".join(body_parts)

    db.upsert_entry({
        "id": entry_id,
        "kb_name": kb_name,
        "title": title,
        "entry_type": "note",
        "body": body,
        "importance": 8,
        "tags": ["investigation"],
        "metadata": {"investigation_status": "active"},
    })

    result: dict[str, Any] = {"created": entry_id, "title": title}

    # Create initial entities
    if initial_entities:
        entities_created = []
        for ent in initial_entities:
            ent_name = ent.get("name", "")
            ent_type = ent.get("type", "person")
            if not ent_name:
                continue
            ent_id = generate_entry_id(ent_name)
            db.upsert_entry({
                "id": ent_id,
                "kb_name": kb_name,
                "title": ent_name,
                "entry_type": ent_type,
                "importance": 5,
                "tags": ["investigation"],
            })
            entities_created.append({"id": ent_id, "title": ent_name, "type": ent_type})
        result["entities_created"] = entities_created

    return result


def build_investigation_status(
    db: Any,
    kb_name: str,
) -> dict[str, Any]:
    """Build a comprehensive investigation status report.

    Gathers counts of entities, events, claims, and sources,
    identifies unverified claims, and produces a summary.
    """
    # Count entities
    entity_count = 0
    for aliases in ENTITY_TYPE_ALIASES.values():
        for etype in aliases:
            try:
                results = db.list_entries(kb_name=kb_name, entry_type=etype, limit=10000)
                entity_count += len(results)
            except Exception:
                pass

    # Count events
    event_types = ["investigation_event", "transaction", "legal_action"]
    event_count = 0
    for etype in event_types:
        try:
            results = db.list_entries(kb_name=kb_name, entry_type=etype, limit=10000)
            event_count += len(results)
        except Exception:
            pass

    # Count and break down claims
    claim_results = db.list_entries(kb_name=kb_name, entry_type="claim", limit=10000)
    claim_count = len(claim_results)
    claim_breakdown: dict[str, int] = {}
    unverified_claims: list[dict[str, Any]] = []

    for r in claim_results:
        meta = parse_meta(r)
        status = meta.get("claim_status", "unverified")
        claim_breakdown[status] = claim_breakdown.get(status, 0) + 1
        if status == "unverified":
            unverified_claims.append({
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "importance": int(r.get("importance", 5)),
            })

    # Count sources
    source_results = db.list_entries(kb_name=kb_name, entry_type="document_source", limit=10000)
    source_count = len(source_results)

    # Build summary
    parts = [
        f"{entity_count} entities",
        f"{event_count} events",
        f"{claim_count} claims",
        f"{source_count} sources",
    ]
    if unverified_claims:
        parts.append(f"{len(unverified_claims)} unverified claims need attention")
    summary = f"Investigation has {', '.join(parts[:4])}."
    if unverified_claims:
        summary += f" {len(unverified_claims)} unverified claims need attention."

    return {
        "summary": summary,
        "entity_count": entity_count,
        "event_count": event_count,
        "claim_count": claim_count,
        "source_count": source_count,
        "claim_breakdown": claim_breakdown,
        "unverified_claims": unverified_claims,
    }
