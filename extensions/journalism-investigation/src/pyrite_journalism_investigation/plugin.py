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
        return {}  # MCP tools will be added in ji-mcp-tools-read-tier


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
