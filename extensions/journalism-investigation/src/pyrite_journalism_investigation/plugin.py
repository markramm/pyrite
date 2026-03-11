"""Journalism Investigation plugin for pyrite."""

from typing import Any

from .preset import JOURNALISM_INVESTIGATION_PRESET
from .entry_types import (
    AccountEntry,
    AssetEntry,
    DocumentSourceEntry,
    InvestigationEventEntry,
    LegalActionEntry,
    TransactionEntry,
)


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
        }

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
        }

    def get_validators(self) -> list:
        return [_validate_investigation_entry]

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
    # MCP tool handlers
    # =========================================================================

    def _mcp_timeline(self, args: dict[str, Any]) -> dict[str, Any]:
        """Query investigation events by date range, actor, and type."""
        import json

        db, should_close = self._get_db()
        kb_name = args["kb_name"]
        from_date = args.get("from_date", "")
        to_date = args.get("to_date", "")
        actor_filter = args.get("actor", "").lower()
        event_type = args.get("event_type", "")
        min_importance = args.get("min_importance", 0)
        limit = args.get("limit", 50)

        event_types = ["investigation_event", "transaction", "legal_action"]
        if event_type and event_type in event_types:
            event_types = [event_type]

        try:
            events = []
            for etype in event_types:
                results = db.list_entries(kb_name=kb_name, entry_type=etype, limit=5000)
                for r in results:
                    imp = int(r.get("importance", 5))
                    if min_importance and imp < min_importance:
                        continue
                    date = str(r.get("date", ""))
                    if from_date and date < from_date:
                        continue
                    if to_date and date > to_date:
                        continue
                    meta = r.get("metadata") or {}
                    if isinstance(meta, str):
                        try:
                            meta = json.loads(meta)
                        except (json.JSONDecodeError, TypeError):
                            meta = {}
                    actors = meta.get("actors") or []
                    if actor_filter and not any(actor_filter in a.lower() for a in actors):
                        continue
                    events.append({
                        "id": r.get("id"),
                        "title": r.get("title"),
                        "type": etype,
                        "date": date,
                        "importance": imp,
                        "actors": actors,
                    })
                    if len(events) >= limit:
                        break
                if len(events) >= limit:
                    break
            events.sort(key=lambda e: e.get("date", ""))
            return {"count": len(events), "events": events[:limit]}
        finally:
            if should_close:
                db.close()

    def _mcp_entities(self, args: dict[str, Any]) -> dict[str, Any]:
        """Query investigation entities."""
        import json

        db, should_close = self._get_db()
        kb_name = args["kb_name"]
        entity_type = args.get("entity_type", "")
        min_importance = args.get("min_importance", 0)
        jurisdiction_filter = args.get("jurisdiction", "").lower()
        limit = args.get("limit", 50)

        entity_types = ["person", "organization", "asset", "account"]
        if entity_type and entity_type in entity_types:
            entity_types = [entity_type]

        try:
            entities = []
            for etype in entity_types:
                results = db.list_entries(kb_name=kb_name, entry_type=etype, limit=5000)
                for r in results:
                    imp = int(r.get("importance", 5))
                    if min_importance and imp < min_importance:
                        continue
                    meta = r.get("metadata") or {}
                    if isinstance(meta, str):
                        try:
                            meta = json.loads(meta)
                        except (json.JSONDecodeError, TypeError):
                            meta = {}
                    jurisdiction = str(meta.get("jurisdiction", "")).lower()
                    if jurisdiction_filter and jurisdiction_filter not in jurisdiction:
                        continue
                    entities.append({
                        "id": r.get("id"),
                        "title": r.get("title"),
                        "type": etype,
                        "importance": imp,
                    })
            entities.sort(key=lambda e: e["importance"], reverse=True)
            return {"count": len(entities[:limit]), "entities": entities[:limit]}
        finally:
            if should_close:
                db.close()

    def _mcp_network(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get connection network for an entity."""
        db, should_close = self._get_db()
        entry_id = args["entry_id"]
        kb_name = args["kb_name"]

        try:
            entry = db.get_entry(entry_id, kb_name)
            if not entry:
                return {"error": f"Entry '{entry_id}' not found"}

            outlinks = db.get_outlinks(entry_id, kb_name)
            backlinks = db.get_backlinks(entry_id, kb_name)

            return {
                "center": {"id": entry_id, "title": entry.get("title", "")},
                "outlinks": outlinks,
                "backlinks": backlinks,
            }
        finally:
            if should_close:
                db.close()

    def _mcp_sources(self, args: dict[str, Any]) -> dict[str, Any]:
        """Query source documents."""
        import json

        db, should_close = self._get_db()
        kb_name = args["kb_name"]
        reliability_filter = args.get("reliability", "")
        classification_filter = args.get("classification", "")
        from_date = args.get("from_date", "")
        to_date = args.get("to_date", "")
        limit = args.get("limit", 50)

        try:
            results = db.list_entries(kb_name=kb_name, entry_type="document_source", limit=5000)
            sources = []
            for r in results:
                meta = r.get("metadata") or {}
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except (json.JSONDecodeError, TypeError):
                        meta = {}
                reliability = meta.get("reliability", "unknown")
                if reliability_filter and reliability != reliability_filter:
                    continue
                classification = meta.get("classification", "")
                if classification_filter and classification != classification_filter:
                    continue
                date = str(r.get("date", meta.get("obtained_date", "")))
                if from_date and date < from_date:
                    continue
                if to_date and date > to_date:
                    continue
                sources.append({
                    "id": r.get("id"),
                    "title": r.get("title"),
                    "reliability": reliability,
                    "classification": classification,
                    "date": date,
                })
            sources.sort(key=lambda s: s.get("date", ""))
            return {"count": len(sources[:limit]), "sources": sources[:limit]}
        finally:
            if should_close:
                db.close()


def _validate_investigation_entry(entry: Any) -> list[str]:
    """Validate journalism-investigation entries."""
    errors = []
    entry_type = getattr(entry, "entry_type", "")

    if entry_type == "asset":
        if not getattr(entry, "asset_type", ""):
            errors.append("Asset must have an asset_type")

    if entry_type == "account":
        if not getattr(entry, "account_type", ""):
            errors.append("Account must have an account_type")

    if entry_type == "document_source":
        if not getattr(entry, "reliability", ""):
            errors.append("Document source must have a reliability level")

    if entry_type == "investigation_event":
        if not getattr(entry, "date", ""):
            errors.append("Investigation event must have a date")

    if entry_type == "transaction":
        if not getattr(entry, "date", ""):
            errors.append("Transaction must have a date")
        txn_type = getattr(entry, "transaction_type", "")
        if txn_type in ("payment", "bribe", "kickback"):
            if not getattr(entry, "amount", ""):
                errors.append(f"Transaction of type '{txn_type}' must have an amount")
        if not getattr(entry, "sender", ""):
            errors.append("Transaction must have a sender")
        if not getattr(entry, "receiver", ""):
            errors.append("Transaction must have a receiver")

    if entry_type == "legal_action":
        if not getattr(entry, "date", ""):
            errors.append("Legal action must have a date")
        if not getattr(entry, "case_type", ""):
            errors.append("Legal action must have a case_type")
        if not getattr(entry, "jurisdiction", ""):
            errors.append("Legal action must have a jurisdiction")

    importance = getattr(entry, "importance", None)
    if importance is not None and isinstance(importance, int):
        if importance < 1 or importance > 10:
            errors.append(f"Importance must be 1-10, got: {importance}")

    return errors
