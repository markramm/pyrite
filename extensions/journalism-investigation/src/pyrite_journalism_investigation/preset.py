"""Journalism Investigation KB preset definition."""

JOURNALISM_INVESTIGATION_PRESET = {
    "name": "my-investigation",
    "description": "Investigative journalism knowledge base with entities, events, sources, and relationship tracking",
    "types": {
        # Core types reused from pyrite
        "person": {
            "description": "A person of interest in the investigation",
            "required": ["title"],
            "optional": ["role", "affiliations", "importance", "research_status"],
            "subdirectory": "entities/",
        },
        "organization": {
            "description": "A company, government body, NGO, or other organization",
            "required": ["title"],
            "optional": ["org_type", "jurisdiction", "founded", "importance", "research_status"],
            "subdirectory": "entities/",
        },
        # Entity types from journalism-investigation plugin
        "asset": {
            "description": "A tracked asset — real estate, vehicle, vessel, aircraft, etc.",
            "required": ["title"],
            "optional": ["asset_type", "value", "currency", "jurisdiction", "registered_owner", "acquisition_date", "description", "importance"],
            "subdirectory": "entities/",
        },
        "account": {
            "description": "A financial account — bank, brokerage, crypto wallet, shell company, trust",
            "required": ["title"],
            "optional": ["account_type", "institution", "jurisdiction", "holder", "opened_date", "closed_date", "importance"],
            "subdirectory": "entities/",
        },
        "document_source": {
            "description": "A source document with reliability and classification metadata",
            "required": ["title"],
            "optional": ["reliability", "classification", "obtained_date", "obtained_method", "date", "author", "url", "importance"],
            "subdirectory": "sources/",
        },
        # Event types from journalism-investigation plugin
        "investigation_event": {
            "description": "A dated event in the investigation with actors and verification status",
            "required": ["title"],
            "optional": ["date", "actors", "source_refs", "verification_status", "location", "importance"],
            "subdirectory": "events/",
        },
        "transaction": {
            "description": "A financial transaction — payment, bribe, grant, etc.",
            "required": ["title"],
            "optional": ["date", "amount", "currency", "sender", "receiver", "method", "purpose", "transaction_type", "importance"],
            "subdirectory": "events/",
        },
        "legal_action": {
            "description": "A legal or regulatory action — case, indictment, sanctions, etc.",
            "required": ["title"],
            "optional": ["date", "case_type", "jurisdiction", "parties", "case_status", "outcome", "case_number", "importance"],
            "subdirectory": "events/",
        },
        # Claim type
        "claim": {
            "description": "A factual assertion with verification lifecycle tracking",
            "required": ["title"],
            "optional": ["assertion", "confidence", "claim_status", "evidence_refs", "disputed_by", "importance"],
            "subdirectory": "claims/",
        },
        # General-purpose types
        "note": {
            "description": "General research note or analysis",
            "required": ["title"],
            "optional": ["importance"],
            "subdirectory": "notes/",
        },
    },
    "policies": {
        "source_tracking": True,
    },
    "validation": {
        "enforce": True,
        "rules": [],
    },
    "directories": ["entities", "events", "sources", "claims", "notes"],
}
