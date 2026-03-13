"""Promote a corroborated claim to an edge-entity (ownership, membership, funding)."""

from typing import Any

from pyrite.schema import generate_entry_id
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB


PROMOTABLE_STATUSES = {"corroborated", "partially_verified"}
VALID_EDGE_TYPES = {"ownership", "membership", "funding"}


def promote_claim_to_edge(
    *,
    db: PyriteDB,
    kb_name: str,
    claim_id: str,
    edge_type: str,
    kb_service: KBService,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Convert a corroborated claim into an edge-entity entry.

    Args:
        db: Database instance for reading the claim.
        kb_name: Knowledge base name.
        claim_id: ID of the claim entry to promote.
        edge_type: Edge type to create (ownership, membership, funding).
        kb_service: KBService for creating the new entry.
        dry_run: If True, return what would be created without creating.

    Returns:
        Result dict with created entry info, or error dict.
    """
    # Validate edge_type
    if edge_type not in VALID_EDGE_TYPES:
        return {"error": f"Invalid edge_type: {edge_type}. Must be one of {VALID_EDGE_TYPES}"}

    # Load the claim from DB
    claim = db.get_entry(claim_id, kb_name)
    if claim is None:
        return {"error": f"Claim not found: {claim_id}"}

    # Verify claim type
    if claim.get("entry_type") != "claim":
        return {"error": f"Entry {claim_id} is not a claim (type: {claim.get('entry_type')})"}

    # Check claim status from metadata
    metadata = claim.get("metadata", {})
    claim_status = metadata.get("claim_status", "unverified")
    if claim_status not in PROMOTABLE_STATUSES:
        return {
            "error": (
                f"Claim {claim_id} has status '{claim_status}'. "
                f"Only claims with status {PROMOTABLE_STATUSES} can be promoted."
            )
        }

    # Derive edge entry properties from the claim
    claim_title = claim.get("title", "")
    edge_title = f"{claim_title} [{edge_type}]"
    edge_id = generate_entry_id(edge_title)
    importance = claim.get("importance", 5)

    # Build the proposed entry info
    proposed = {
        "entry_id": edge_id,
        "title": edge_title,
        "edge_type": edge_type,
        "importance": importance,
        "sourced_from": claim_id,
    }

    if dry_run:
        return {
            "dry_run": True,
            "proposed": proposed,
            "edge_type": edge_type,
            "source_claim": claim_id,
        }

    # Create the edge-entity entry
    try:
        kb_service.create_entry(
            kb_name=kb_name,
            entry_id=edge_id,
            title=edge_title,
            entry_type=edge_type,
            body=f"Promoted from claim [[{claim_id}]].",
            importance=importance,
            links=[
                {"target": claim_id, "relation": "sourced_from"},
            ],
        )
        return {
            "created": edge_id,
            "edge_type": edge_type,
            "title": edge_title,
            "source_claim": claim_id,
        }
    except Exception as e:
        return {"error": str(e)}
