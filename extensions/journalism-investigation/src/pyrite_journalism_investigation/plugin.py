"""Journalism Investigation plugin for pyrite."""

from typing import Any

from .preset import JOURNALISM_INVESTIGATION_PRESET
from .entry_types import (
    AccountEntry,
    AssetEntry,
    ClaimEntry,
    DocumentSourceEntry,
    EvidenceEntry,
    FundingEntry,
    InvestigationEventEntry,
    LegalActionEntry,
    MembershipEntry,
    OwnershipEntry,
    TransactionEntry,
)
from .hooks import enrich_connection_links
from .queries import (
    ENTITY_TYPE_ALIASES,
    query_claims,
    query_entities,
    query_evidence_chain,
    query_network,
    query_sources,
    query_timeline,
)
from .utils import parse_meta
from .validators import validate_investigation_entry


class JournalismInvestigationPlugin:
    """Journalism Investigation plugin for pyrite.

    Provides entry types for investigative journalism research:
    entities (asset, account, document_source), events (investigation_event,
    transaction, legal_action), and investigation-specific relationship types.
    """

    name = "journalism_investigation"

    def __init__(self):
        self.ctx = None

    def set_context(self, ctx) -> None:
        """Receive shared dependencies from the plugin infrastructure."""
        self.ctx = ctx

    def get_entry_types(self) -> dict[str, type]:
        return {
            "asset": AssetEntry,
            "account": AccountEntry,
            "document_source": DocumentSourceEntry,
            "investigation_event": InvestigationEventEntry,
            "transaction": TransactionEntry,
            "legal_action": LegalActionEntry,
            "claim": ClaimEntry,
            "evidence": EvidenceEntry,
            "ownership": OwnershipEntry,
            "membership": MembershipEntry,
            "funding": FundingEntry,
        }

    def get_cli_commands(self) -> list[tuple[str, Any]]:
        from .cli import investigation_app

        return [("investigation", investigation_app)]

    def get_kb_types(self) -> list[str]:
        return ["journalism-investigation"]

    def get_kb_presets(self) -> dict[str, dict]:
        return {"journalism-investigation": JOURNALISM_INVESTIGATION_PRESET}

    def get_relationship_types(self) -> dict[str, dict]:
        # Note: member_of/has_member, funded_by/funds, investigated/investigated_by
        # are already registered by the cascade plugin. We only register types
        # that are new to journalism-investigation.
        return {
            "owns": {
                "inverse": "owned_by",
                "description": "Entity owns an asset or organization",
            },
            "owned_by": {
                "inverse": "owns",
                "description": "Asset or organization is owned by an entity",
            },
            "sourced_from": {
                "inverse": "source_for",
                "description": "Claim or fact is sourced from a document",
            },
            "source_for": {
                "inverse": "sourced_from",
                "description": "Document is a source for a claim or fact",
            },
            "corroborates": {
                "inverse": "corroborated_by",
                "description": "Evidence corroborates a claim",
            },
            "corroborated_by": {
                "inverse": "corroborates",
                "description": "Claim is corroborated by evidence",
            },
            "contradicts": {
                "inverse": "contradicted_by",
                "description": "Evidence contradicts a claim",
            },
            "contradicted_by": {
                "inverse": "contradicts",
                "description": "Claim is contradicted by evidence",
            },
            "beneficial_owner_of": {
                "inverse": "beneficially_owned_by",
                "description": "Person is the beneficial owner of an entity",
            },
            "beneficially_owned_by": {
                "inverse": "beneficial_owner_of",
                "description": "Entity is beneficially owned by a person",
            },
            "transacted_with": {
                "inverse": "received_transaction_from",
                "description": "Entity transacted with another entity",
            },
            "received_transaction_from": {
                "inverse": "transacted_with",
                "description": "Entity received a transaction from another entity",
            },
            "party_to": {
                "inverse": "has_party",
                "description": "Entity is a party to a legal action",
            },
            "has_party": {
                "inverse": "party_to",
                "description": "Legal action has an entity as a party",
            },
            "supports": {
                "inverse": "supported_by",
                "description": "Evidence supports a claim",
            },
            "supported_by": {
                "inverse": "supports",
                "description": "Claim is supported by evidence",
            },
        }

    def get_validators(self) -> list:
        return [validate_investigation_entry]

    def get_hooks(self) -> dict[str, list]:
        return {"before_save": [enrich_connection_links]}

    def get_mcp_tools(self, tier: str) -> dict[str, dict]:
        tools: dict[str, dict[str, Any]] = {}
        if tier in ("read", "write", "admin"):
            tools["investigation_timeline"] = {
                "description": "Query investigation events by date range, actor, event type, and importance",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "from_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                        "to_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                        "actor": {"type": "string", "description": "Filter by actor name (substring match)"},
                        "event_type": {"type": "string", "description": "Filter by type: investigation_event, transaction, legal_action"},
                        "min_importance": {"type": "integer", "description": "Minimum importance (1-10)"},
                        "limit": {"type": "integer", "description": "Max results (default 50)"},
                        "kb_name": {"type": "string", "description": "KB name"},
                    },
                    "required": ["kb_name"],
                },
                "handler": self._mcp_timeline,
            }
            tools["investigation_entities"] = {
                "description": "Query investigation entities (person, organization, asset, account) by type, importance, and jurisdiction",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string", "description": "Filter by type: person, organization, asset, account"},
                        "min_importance": {"type": "integer", "description": "Minimum importance (1-10)"},
                        "jurisdiction": {"type": "string", "description": "Filter by jurisdiction (substring match)"},
                        "limit": {"type": "integer", "description": "Max results (default 50)"},
                        "kb_name": {"type": "string", "description": "KB name"},
                    },
                    "required": ["kb_name"],
                },
                "handler": self._mcp_entities,
            }
            tools["investigation_network"] = {
                "description": "Get the connection network for an entity — all outlinks, backlinks, and related entries",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entry_id": {"type": "string", "description": "Entry ID to get network for"},
                        "kb_name": {"type": "string", "description": "KB name"},
                    },
                    "required": ["entry_id", "kb_name"],
                },
                "handler": self._mcp_network,
            }
            tools["investigation_sources"] = {
                "description": "Query source documents by reliability, classification, and date range",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "reliability": {"type": "string", "description": "Filter by reliability: high, medium, low, unknown"},
                        "classification": {"type": "string", "description": "Filter by classification: public, leaked, foia, court_filing, etc."},
                        "from_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                        "to_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                        "limit": {"type": "integer", "description": "Max results (default 50)"},
                        "kb_name": {"type": "string", "description": "KB name"},
                    },
                    "required": ["kb_name"],
                },
                "handler": self._mcp_sources,
            }
            tools["investigation_claims"] = {
                "description": "Query claims by status, confidence level, and importance",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "claim_status": {"type": "string", "description": "Filter by status: unverified, partially_verified, corroborated, disputed, retracted"},
                        "confidence": {"type": "string", "description": "Filter by confidence: high, medium, low"},
                        "min_importance": {"type": "integer", "description": "Minimum importance (1-10)"},
                        "limit": {"type": "integer", "description": "Max results (default 50)"},
                        "kb_name": {"type": "string", "description": "KB name"},
                    },
                    "required": ["kb_name"],
                },
                "handler": self._mcp_claims,
            }
            tools["investigation_evidence_chain"] = {
                "description": "Trace the evidence chain for a claim: claim → evidence entries → source documents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "claim_id": {"type": "string", "description": "Claim entry ID to trace"},
                        "kb_name": {"type": "string", "description": "KB name"},
                    },
                    "required": ["claim_id", "kb_name"],
                },
                "handler": self._mcp_evidence_chain,
            }
            tools["investigation_qa_report"] = {
                "description": "Get investigation quality metrics: source reliability, claim coverage, orphan claims, quality score, and warnings",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name"},
                        "stale_days": {"type": "integer", "description": "Days before unverified claims are stale (default 30)"},
                    },
                    "required": ["kb_name"],
                },
                "handler": self._mcp_qa_report,
            }
        if tier in ("write", "admin"):
            tools["investigation_create_entity"] = {
                "description": "Create a person, organization, asset, or account entity in the investigation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string", "description": "Type: person, organization, asset, account"},
                        "title": {"type": "string", "description": "Entity name/title"},
                        "body": {"type": "string", "description": "Description and context"},
                        "importance": {"type": "integer", "description": "Importance 1-10 (default 5)"},
                        "fields": {"type": "object", "description": "Type-specific fields (e.g. asset_type, jurisdiction)"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags"},
                        "kb_name": {"type": "string", "description": "KB name"},
                    },
                    "required": ["entity_type", "title", "kb_name"],
                },
                "handler": self._mcp_create_entity,
            }
            tools["investigation_create_event"] = {
                "description": "Create an investigation event, transaction, or legal action",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "event_type": {"type": "string", "description": "Type: investigation_event, transaction, legal_action"},
                        "title": {"type": "string", "description": "Event title"},
                        "date": {"type": "string", "description": "Event date (YYYY-MM-DD)"},
                        "body": {"type": "string", "description": "Narrative context"},
                        "importance": {"type": "integer", "description": "Importance 1-10 (default 5)"},
                        "fields": {"type": "object", "description": "Type-specific fields (e.g. sender, receiver, case_type)"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags"},
                        "kb_name": {"type": "string", "description": "KB name"},
                    },
                    "required": ["event_type", "title", "date", "kb_name"],
                },
                "handler": self._mcp_create_event,
            }
            tools["investigation_create_claim"] = {
                "description": "Create a factual claim with evidence links for verification tracking",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Claim title"},
                        "assertion": {"type": "string", "description": "The specific factual assertion"},
                        "evidence_refs": {"type": "array", "items": {"type": "string"}, "description": "Wikilinks to evidence entries"},
                        "body": {"type": "string", "description": "Narrative context"},
                        "importance": {"type": "integer", "description": "Importance 1-10 (default 5)"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags"},
                        "kb_name": {"type": "string", "description": "KB name"},
                    },
                    "required": ["title", "assertion", "kb_name"],
                },
                "handler": self._mcp_create_claim,
            }
            tools["investigation_log_source"] = {
                "description": "Log a source document with reliability and classification metadata",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Source document title"},
                        "url": {"type": "string", "description": "Source URL"},
                        "reliability": {"type": "string", "description": "Reliability: high, medium, low, unknown"},
                        "classification": {"type": "string", "description": "Classification: public, leaked, foia, court_filing, etc."},
                        "obtained_method": {"type": "string", "description": "How the source was obtained"},
                        "body": {"type": "string", "description": "Notes about the source"},
                        "importance": {"type": "integer", "description": "Importance 1-10 (default 5)"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags"},
                        "kb_name": {"type": "string", "description": "KB name"},
                    },
                    "required": ["title", "kb_name"],
                },
                "handler": self._mcp_log_source,
            }
        return tools

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _get_db(self):
        """Get DB from injected context, falling back to self-bootstrap."""
        if self.ctx is not None:
            return self.ctx.db, False
        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        return PyriteDB(config.settings.index_path), True

    # =========================================================================
    # Read-tier MCP tool handlers — delegate to pure query functions
    # =========================================================================

    def _mcp_timeline(self, args: dict[str, Any]) -> dict[str, Any]:
        db, should_close = self._get_db()
        try:
            return query_timeline(
                db, args["kb_name"],
                from_date=args.get("from_date", ""),
                to_date=args.get("to_date", ""),
                actor=args.get("actor", ""),
                event_type=args.get("event_type", ""),
                min_importance=args.get("min_importance", 0),
                limit=args.get("limit", 50),
            )
        finally:
            if should_close:
                db.close()

    def _mcp_entities(self, args: dict[str, Any]) -> dict[str, Any]:
        db, should_close = self._get_db()
        try:
            return query_entities(
                db, args["kb_name"],
                entity_type=args.get("entity_type", ""),
                min_importance=args.get("min_importance", 0),
                jurisdiction=args.get("jurisdiction", ""),
                limit=args.get("limit", 50),
            )
        finally:
            if should_close:
                db.close()

    def _mcp_network(self, args: dict[str, Any]) -> dict[str, Any]:
        db, should_close = self._get_db()
        try:
            return query_network(db, args["kb_name"], args["entry_id"])
        finally:
            if should_close:
                db.close()

    def _mcp_sources(self, args: dict[str, Any]) -> dict[str, Any]:
        db, should_close = self._get_db()
        try:
            return query_sources(
                db, args["kb_name"],
                reliability=args.get("reliability", ""),
                classification=args.get("classification", ""),
                from_date=args.get("from_date", ""),
                to_date=args.get("to_date", ""),
                limit=args.get("limit", 50),
            )
        finally:
            if should_close:
                db.close()

    def _mcp_claims(self, args: dict[str, Any]) -> dict[str, Any]:
        db, should_close = self._get_db()
        try:
            return query_claims(
                db, args["kb_name"],
                claim_status=args.get("claim_status", ""),
                confidence=args.get("confidence", ""),
                min_importance=args.get("min_importance", 0),
                limit=args.get("limit", 50),
            )
        finally:
            if should_close:
                db.close()

    def _mcp_evidence_chain(self, args: dict[str, Any]) -> dict[str, Any]:
        db, should_close = self._get_db()
        try:
            return query_evidence_chain(db, args["kb_name"], args["claim_id"])
        finally:
            if should_close:
                db.close()

    def _mcp_qa_report(self, args: dict[str, Any]) -> dict[str, Any]:
        from .qa import compute_qa_metrics

        db, should_close = self._get_db()
        try:
            return compute_qa_metrics(
                db, args["kb_name"],
                stale_days=args.get("stale_days", 30),
            )
        finally:
            if should_close:
                db.close()

    # =========================================================================
    # Write-tier MCP tool handlers
    # =========================================================================

    def _get_kb_service(self):
        """Get KBService from context."""
        if self.ctx is not None and hasattr(self.ctx, "kb_service"):
            return self.ctx.kb_service
        return None

    def _mcp_create_entity(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create an entity entry."""
        from pyrite.schema import generate_entry_id

        kb_name = args["kb_name"]
        entity_type = args["entity_type"]
        title = args["title"]

        valid_types = {"person", "organization", "asset", "account"}
        if entity_type not in valid_types:
            return {"error": f"Invalid entity_type: {entity_type}. Must be one of {valid_types}"}

        entry_id = generate_entry_id(title)
        fields = args.get("fields", {}) or {}

        kb_service = self._get_kb_service()
        if kb_service is None:
            return {"error": "No KB service available — write tools require a running server context"}

        try:
            kb_service.create_entry(
                kb_name=kb_name,
                entry_id=entry_id,
                title=title,
                entry_type=entity_type,
                body=args.get("body", ""),
                importance=args.get("importance", 5),
                tags=args.get("tags", []),
                **fields,
            )
            return {"created": entry_id, "type": entity_type, "title": title}
        except Exception as e:
            return {"error": str(e)}

    def _mcp_create_event(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create an event entry."""
        from pyrite.schema import generate_entry_id

        kb_name = args["kb_name"]
        event_type = args["event_type"]
        title = args["title"]
        date = args["date"]

        valid_types = {"investigation_event", "transaction", "legal_action"}
        if event_type not in valid_types:
            return {"error": f"Invalid event_type: {event_type}. Must be one of {valid_types}"}

        entry_id = generate_entry_id(title)
        fields = args.get("fields", {}) or {}

        kb_service = self._get_kb_service()
        if kb_service is None:
            return {"error": "No KB service available — write tools require a running server context"}

        try:
            kb_service.create_entry(
                kb_name=kb_name,
                entry_id=entry_id,
                title=title,
                entry_type=event_type,
                body=args.get("body", ""),
                date=date,
                importance=args.get("importance", 5),
                tags=args.get("tags", []),
                **fields,
            )
            return {"created": entry_id, "type": event_type, "title": title}
        except Exception as e:
            return {"error": str(e)}

    def _mcp_create_claim(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a claim entry."""
        from pyrite.schema import generate_entry_id

        kb_name = args["kb_name"]
        title = args["title"]
        assertion = args["assertion"]

        entry_id = generate_entry_id(title)
        evidence_refs = args.get("evidence_refs", []) or []
        warnings = []

        if not evidence_refs:
            warnings.append("Claim created with no evidence references — mark for follow-up")

        kb_service = self._get_kb_service()
        if kb_service is None:
            return {"error": "No KB service available — write tools require a running server context"}

        try:
            kb_service.create_entry(
                kb_name=kb_name,
                entry_id=entry_id,
                title=title,
                entry_type="claim",
                body=args.get("body", ""),
                assertion=assertion,
                claim_status="unverified",
                confidence="low",
                evidence_refs=evidence_refs,
                importance=args.get("importance", 5),
                tags=args.get("tags", []),
            )
            result: dict[str, Any] = {"created": entry_id, "type": "claim", "title": title}
            if warnings:
                result["warnings"] = warnings
            return result
        except Exception as e:
            return {"error": str(e)}

    def _mcp_log_source(self, args: dict[str, Any]) -> dict[str, Any]:
        """Log a source document."""
        from pyrite.schema import generate_entry_id

        kb_name = args["kb_name"]
        title = args["title"]

        entry_id = generate_entry_id(title)

        kb_service = self._get_kb_service()
        if kb_service is None:
            return {"error": "No KB service available — write tools require a running server context"}

        try:
            kb_service.create_entry(
                kb_name=kb_name,
                entry_id=entry_id,
                title=title,
                entry_type="document_source",
                body=args.get("body", ""),
                reliability=args.get("reliability", "unknown"),
                classification=args.get("classification", ""),
                url=args.get("url", ""),
                obtained_method=args.get("obtained_method", ""),
                importance=args.get("importance", 5),
                tags=args.get("tags", []),
            )
            return {"created": entry_id, "type": "document_source", "title": title}
        except Exception as e:
            return {"error": str(e)}


# Backward-compatible aliases for external code that imports private names
_parse_meta = parse_meta
_validate_investigation_entry = validate_investigation_entry
