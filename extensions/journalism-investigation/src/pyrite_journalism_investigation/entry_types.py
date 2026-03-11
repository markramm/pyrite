"""Journalism Investigation entry types for investigative research."""

from dataclasses import dataclass, field
from typing import Any

from pyrite.models.base import Entry, parse_datetime, parse_links, parse_sources
from pyrite.models.core_types import DocumentEntry, EventEntry
from pyrite.schema import EventStatus, Provenance, generate_entry_id


# ---------------------------------------------------------------------------
# Helper: build common kwargs from frontmatter meta dict
# ---------------------------------------------------------------------------

def _base_kwargs(meta: dict[str, Any], body: str) -> dict[str, Any]:
    """Extract base Entry fields from frontmatter dict."""
    prov_data = meta.get("provenance")
    provenance = Provenance.from_dict(prov_data) if prov_data else None

    entry_id = meta.get("id", "")
    if not entry_id:
        entry_id = generate_entry_id(meta.get("title", ""))

    return {
        "id": str(entry_id),
        "title": meta.get("title", ""),
        "body": body,
        "summary": meta.get("summary", ""),
        "tags": meta.get("tags", []) or [],
        "aliases": meta.get("aliases", []) or [],
        "sources": parse_sources(meta.get("sources")),
        "links": parse_links(meta.get("links")),
        "provenance": provenance,
        "metadata": meta.get("metadata", {}),
        "created_at": parse_datetime(meta.get("created_at")),
        "updated_at": parse_datetime(meta.get("updated_at")),
    }


# ---------------------------------------------------------------------------
# Entity types
# ---------------------------------------------------------------------------

# Enum tuples for validation
ASSET_TYPES = (
    "real_estate", "vehicle", "vessel", "aircraft",
    "luxury_good", "intellectual_property", "other",
)
ACCOUNT_TYPES = (
    "bank", "brokerage", "crypto_wallet",
    "shell_company", "trust", "other",
)
RELIABILITY_LEVELS = ("high", "medium", "low", "unknown")
CLASSIFICATIONS = (
    "public", "leaked", "foia", "court_filing",
    "financial_disclosure", "corporate_registry", "other",
)

# Event enum tuples
VERIFICATION_STATUSES = ("unverified", "partially_verified", "verified", "disputed")
TRANSACTION_METHODS = ("wire", "cash", "crypto", "check", "other")
TRANSACTION_TYPES = (
    "payment", "grant", "donation", "loan",
    "investment", "bribe", "kickback", "other",
)
CASE_TYPES = (
    "criminal", "civil", "regulatory", "sanctions",
    "indictment", "subpoena", "other",
)
CASE_STATUSES = (
    "filed", "pending", "settled", "dismissed",
    "convicted", "acquitted",
)

# Claim enum tuples
CLAIM_STATUSES = (
    "unverified", "partially_verified", "corroborated", "disputed", "retracted",
)
CONFIDENCE_LEVELS = ("high", "medium", "low")


@dataclass
class AssetEntry(Entry):
    """A tracked asset — real estate, vehicle, vessel, etc."""

    asset_type: str = ""
    value: str = ""
    currency: str = ""
    jurisdiction: str = ""
    registered_owner: str = ""
    acquisition_date: str = ""
    description: str = ""

    @property
    def entry_type(self) -> str:
        return "asset"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        meta["type"] = "asset"
        if self.asset_type:
            meta["asset_type"] = self.asset_type
        if self.value:
            meta["value"] = self.value
        if self.currency:
            meta["currency"] = self.currency
        if self.jurisdiction:
            meta["jurisdiction"] = self.jurisdiction
        if self.registered_owner:
            meta["registered_owner"] = self.registered_owner
        if self.acquisition_date:
            meta["acquisition_date"] = self.acquisition_date
        if self.description:
            meta["description"] = self.description
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "AssetEntry":
        kw = _base_kwargs(meta, body)
        return cls(
            **kw,
            importance=int(meta.get("importance", 5)),
            asset_type=meta.get("asset_type", ""),
            value=str(meta.get("value", "")),
            currency=meta.get("currency", ""),
            jurisdiction=meta.get("jurisdiction", ""),
            registered_owner=meta.get("registered_owner", ""),
            acquisition_date=str(meta.get("acquisition_date", "")),
            description=meta.get("description", ""),
        )


@dataclass
class AccountEntry(Entry):
    """A financial account — bank, brokerage, crypto wallet, etc."""

    account_type: str = ""
    institution: str = ""
    jurisdiction: str = ""
    holder: str = ""
    opened_date: str = ""
    closed_date: str = ""

    @property
    def entry_type(self) -> str:
        return "account"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        meta["type"] = "account"
        if self.account_type:
            meta["account_type"] = self.account_type
        if self.institution:
            meta["institution"] = self.institution
        if self.jurisdiction:
            meta["jurisdiction"] = self.jurisdiction
        if self.holder:
            meta["holder"] = self.holder
        if self.opened_date:
            meta["opened_date"] = self.opened_date
        if self.closed_date:
            meta["closed_date"] = self.closed_date
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "AccountEntry":
        kw = _base_kwargs(meta, body)
        return cls(
            **kw,
            importance=int(meta.get("importance", 5)),
            account_type=meta.get("account_type", ""),
            institution=meta.get("institution", ""),
            jurisdiction=meta.get("jurisdiction", ""),
            holder=meta.get("holder", ""),
            opened_date=str(meta.get("opened_date", "")),
            closed_date=str(meta.get("closed_date", "")),
        )


@dataclass
class DocumentSourceEntry(DocumentEntry):
    """A source document with reliability and classification metadata."""

    reliability: str = "unknown"
    classification: str = ""
    obtained_date: str = ""
    obtained_method: str = ""

    @property
    def entry_type(self) -> str:
        return "document_source"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "document_source"
        if self.reliability != "unknown":
            meta["reliability"] = self.reliability
        if self.classification:
            meta["classification"] = self.classification
        if self.obtained_date:
            meta["obtained_date"] = self.obtained_date
        if self.obtained_method:
            meta["obtained_method"] = self.obtained_method
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "DocumentSourceEntry":
        kw = _base_kwargs(meta, body)
        return cls(
            **kw,
            importance=int(meta.get("importance", 5)),
            date=meta.get("date", ""),
            author=meta.get("author", ""),
            document_type=meta.get("document_type", ""),
            url=meta.get("url", ""),
            reliability=meta.get("reliability", "unknown"),
            classification=meta.get("classification", ""),
            obtained_date=str(meta.get("obtained_date", "")),
            obtained_method=meta.get("obtained_method", ""),
        )


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


@dataclass
class InvestigationEventEntry(EventEntry):
    """An event in an investigation with actors, source references, and verification status."""

    actors: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    verification_status: str = "unverified"

    @property
    def entry_type(self) -> str:
        return "investigation_event"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "investigation_event"
        if self.actors:
            meta["actors"] = self.actors
        if self.source_refs:
            meta["source_refs"] = self.source_refs
        if self.verification_status != "unverified":
            meta["verification_status"] = self.verification_status
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "InvestigationEventEntry":
        kw = _base_kwargs(meta, body)

        status_str = meta.get("status", "confirmed")
        try:
            status = EventStatus(status_str)
        except ValueError:
            status = EventStatus.CONFIRMED

        return cls(
            **kw,
            date=str(meta.get("date", "")),
            importance=int(meta.get("importance", 5)),
            status=status,
            location=meta.get("location", ""),
            participants=meta.get("participants", []) or [],
            notes=meta.get("notes", ""),
            actors=meta.get("actors", []) or [],
            source_refs=meta.get("source_refs", []) or [],
            verification_status=meta.get("verification_status", "unverified"),
        )


@dataclass
class TransactionEntry(EventEntry):
    """A financial transaction — payment, bribe, grant, etc."""

    amount: str = ""
    currency: str = ""
    sender: str = ""
    receiver: str = ""
    method: str = ""
    purpose: str = ""
    transaction_type: str = ""

    @property
    def entry_type(self) -> str:
        return "transaction"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "transaction"
        if self.amount:
            meta["amount"] = self.amount
        if self.currency:
            meta["currency"] = self.currency
        if self.sender:
            meta["sender"] = self.sender
        if self.receiver:
            meta["receiver"] = self.receiver
        if self.method:
            meta["method"] = self.method
        if self.purpose:
            meta["purpose"] = self.purpose
        if self.transaction_type:
            meta["transaction_type"] = self.transaction_type
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "TransactionEntry":
        kw = _base_kwargs(meta, body)

        status_str = meta.get("status", "confirmed")
        try:
            status = EventStatus(status_str)
        except ValueError:
            status = EventStatus.CONFIRMED

        return cls(
            **kw,
            date=str(meta.get("date", "")),
            importance=int(meta.get("importance", 5)),
            status=status,
            location=meta.get("location", ""),
            participants=meta.get("participants", []) or [],
            notes=meta.get("notes", ""),
            amount=str(meta.get("amount", "")),
            currency=meta.get("currency", ""),
            sender=meta.get("sender", ""),
            receiver=meta.get("receiver", ""),
            method=meta.get("method", ""),
            purpose=meta.get("purpose", ""),
            transaction_type=meta.get("transaction_type", ""),
        )


@dataclass
class LegalActionEntry(EventEntry):
    """A legal or regulatory action — case, indictment, sanctions, etc."""

    case_type: str = ""
    jurisdiction: str = ""
    parties: list[str] = field(default_factory=list)
    case_status: str = ""
    outcome: str = ""
    case_number: str = ""

    @property
    def entry_type(self) -> str:
        return "legal_action"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "legal_action"
        if self.case_type:
            meta["case_type"] = self.case_type
        if self.jurisdiction:
            meta["jurisdiction"] = self.jurisdiction
        if self.parties:
            meta["parties"] = self.parties
        if self.case_status:
            meta["case_status"] = self.case_status
        if self.outcome:
            meta["outcome"] = self.outcome
        if self.case_number:
            meta["case_number"] = self.case_number
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "LegalActionEntry":
        kw = _base_kwargs(meta, body)

        status_str = meta.get("status", "confirmed")
        try:
            status = EventStatus(status_str)
        except ValueError:
            status = EventStatus.CONFIRMED

        return cls(
            **kw,
            date=str(meta.get("date", "")),
            importance=int(meta.get("importance", 5)),
            status=status,
            location=meta.get("location", ""),
            participants=meta.get("participants", []) or [],
            notes=meta.get("notes", ""),
            case_type=meta.get("case_type", ""),
            jurisdiction=meta.get("jurisdiction", ""),
            parties=meta.get("parties", []) or [],
            case_status=meta.get("case_status", ""),
            outcome=meta.get("outcome", ""),
            case_number=meta.get("case_number", ""),
        )


# ---------------------------------------------------------------------------
# Claim type
# ---------------------------------------------------------------------------

# Status transition map: from_status -> set of valid to_statuses
_CLAIM_TRANSITIONS: dict[str, set[str]] = {
    "unverified": {"partially_verified"},
    "partially_verified": {"corroborated", "disputed"},
    "disputed": {"retracted", "corroborated"},
    "corroborated": set(),
    "retracted": set(),
}


@dataclass
class ClaimEntry(Entry):
    """A factual assertion with verification lifecycle tracking."""

    assertion: str = ""
    confidence: str = "low"
    claim_status: str = "unverified"
    evidence_refs: list[str] = field(default_factory=list)
    disputed_by: list[str] = field(default_factory=list)

    @property
    def entry_type(self) -> str:
        return "claim"

    @staticmethod
    def valid_transitions(from_status: str) -> set[str]:
        """Return valid target statuses for a given current status."""
        return _CLAIM_TRANSITIONS.get(from_status, set())

    def can_transition_to(self, target_status: str) -> bool:
        """Check if the claim can transition to the target status."""
        return target_status in self.valid_transitions(self.claim_status)

    def auto_confidence(self, source_tiers: dict[str, int] | None = None) -> str:
        """Calculate confidence from evidence count, tiers, and dispute status.

        Args:
            source_tiers: Optional mapping of evidence_ref -> tier number.
                If provided and sources span multiple tiers, confidence is "high".
        """
        if self.disputed_by:
            return "low"
        if len(self.evidence_refs) < 2:
            return "low"
        # Check for cross-tier corroboration
        if source_tiers is not None:
            tiers = {source_tiers.get(ref, 0) for ref in self.evidence_refs}
            # Filter out default tier (0 = unknown ref)
            tiers.discard(0)
            if len(tiers) >= 2:
                return "high"
        return "medium"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        meta["type"] = "claim"
        if self.assertion:
            meta["assertion"] = self.assertion
        if self.confidence != "low":
            meta["confidence"] = self.confidence
        if self.claim_status != "unverified":
            meta["claim_status"] = self.claim_status
        if self.evidence_refs:
            meta["evidence_refs"] = self.evidence_refs
        if self.disputed_by:
            meta["disputed_by"] = self.disputed_by
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "ClaimEntry":
        kw = _base_kwargs(meta, body)
        return cls(
            **kw,
            importance=int(meta.get("importance", 5)),
            assertion=meta.get("assertion", ""),
            confidence=meta.get("confidence", "low"),
            claim_status=meta.get("claim_status", "unverified"),
            evidence_refs=meta.get("evidence_refs", []) or [],
            disputed_by=meta.get("disputed_by", []) or [],
        )
