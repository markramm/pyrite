"""Validators for journalism-investigation entry types."""

from typing import Any

from .entry_types import (
    ACCOUNT_TYPES,
    ASSET_TYPES,
    CASE_STATUSES,
    CASE_TYPES,
    CLAIM_STATUSES,
    CONFIDENCE_LEVELS,
    EVIDENCE_TYPES,
    FUNDING_MECHANISMS,
    RELIABILITY_LEVELS,
    TRANSACTION_TYPES,
)


def validate_enum(
    value: str, valid_values: tuple[str, ...], field_name: str, errors: list[str],
) -> None:
    """Append an error if value is non-empty and not in valid_values."""
    if value and value not in valid_values:
        errors.append(f"Invalid {field_name}: {value}")


def validate_investigation_entry(entry: Any) -> list[str]:
    """Validate journalism-investigation entries."""
    errors = []
    entry_type = getattr(entry, "entry_type", "")

    if entry_type == "asset":
        if not getattr(entry, "asset_type", ""):
            errors.append("Asset must have an asset_type")
        validate_enum(getattr(entry, "asset_type", ""), ASSET_TYPES, "asset_type", errors)

    if entry_type == "account":
        if not getattr(entry, "account_type", ""):
            errors.append("Account must have an account_type")
        validate_enum(getattr(entry, "account_type", ""), ACCOUNT_TYPES, "account_type", errors)

    if entry_type == "document_source":
        if not getattr(entry, "reliability", ""):
            errors.append("Document source must have a reliability level")
        validate_enum(getattr(entry, "reliability", ""), RELIABILITY_LEVELS, "reliability", errors)

    if entry_type == "investigation_event":
        if not getattr(entry, "date", ""):
            errors.append("Investigation event must have a date")

    if entry_type == "transaction":
        if not getattr(entry, "date", ""):
            errors.append("Transaction must have a date")
        txn_type = getattr(entry, "transaction_type", "")
        validate_enum(txn_type, TRANSACTION_TYPES, "transaction_type", errors)
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
        validate_enum(getattr(entry, "case_type", ""), CASE_TYPES, "case_type", errors)
        if not getattr(entry, "jurisdiction", ""):
            errors.append("Legal action must have a jurisdiction")
        validate_enum(getattr(entry, "case_status", ""), CASE_STATUSES, "case_status", errors)

    if entry_type == "ownership":
        if not getattr(entry, "owner", ""):
            errors.append("Ownership must have an owner")
        if not getattr(entry, "asset", ""):
            errors.append("Ownership must have an asset")

    if entry_type == "membership":
        if not getattr(entry, "person", ""):
            errors.append("Membership must have a person")
        if not getattr(entry, "organization", ""):
            errors.append("Membership must have an organization")

    if entry_type == "funding":
        if not getattr(entry, "funder", ""):
            errors.append("Funding must have a funder")
        if not getattr(entry, "recipient", ""):
            errors.append("Funding must have a recipient")
        validate_enum(getattr(entry, "mechanism", ""), FUNDING_MECHANISMS, "mechanism", errors)

    if entry_type == "evidence":
        if not getattr(entry, "evidence_type", ""):
            errors.append("Evidence must have an evidence_type")
        validate_enum(getattr(entry, "evidence_type", ""), EVIDENCE_TYPES, "evidence_type", errors)

    if entry_type == "claim":
        if not getattr(entry, "assertion", ""):
            errors.append("Claim must have an assertion")
        validate_enum(getattr(entry, "claim_status", ""), CLAIM_STATUSES, "claim_status", errors)
        validate_enum(getattr(entry, "confidence", ""), CONFIDENCE_LEVELS, "confidence", errors)

    importance = getattr(entry, "importance", None)
    if importance is not None and isinstance(importance, int):
        if importance < 1 or importance > 10:
            errors.append(f"Importance must be 1-10, got: {importance}")

    return errors
