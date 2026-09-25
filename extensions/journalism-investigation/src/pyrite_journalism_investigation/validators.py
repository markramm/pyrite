"""Validators for journalism-investigation entry types."""

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
    value: str,
    valid_values: tuple[str, ...],
    field_name: str,
    errors: list[dict],
) -> None:
    """Append an error dict if value is non-empty and not in valid_values."""
    if value and value not in valid_values:
        errors.append(
            {
                "field": field_name,
                "rule": "enum",
                "expected": list(valid_values),
                "got": value,
                "message": f"Invalid {field_name}: {value}",
            }
        )


def _required(field_name: str, value: str, message: str, errors: list[dict]) -> None:
    """Append an error dict if value is falsy."""
    if not value:
        errors.append({"field": field_name, "rule": "required", "message": message})


def validate_investigation_entry(entry_type: str, fields: dict, ctx: dict) -> list[dict]:
    """Validate journalism-investigation entries.

    Plugin validator contract (#379, #376, #48): binds
    (entry_type: str, fields: dict, ctx: dict) and returns a list of issue
    dicts with a `message` (or `field`) key and an optional `severity`
    (default: error).
    """
    errors: list[dict] = []

    if entry_type == "asset":
        _required(
            "asset_type", fields.get("asset_type", ""), "Asset must have an asset_type", errors
        )
        validate_enum(fields.get("asset_type", ""), ASSET_TYPES, "asset_type", errors)

    if entry_type == "account":
        _required(
            "account_type",
            fields.get("account_type", ""),
            "Account must have an account_type",
            errors,
        )
        validate_enum(fields.get("account_type", ""), ACCOUNT_TYPES, "account_type", errors)

    if entry_type == "document_source":
        _required(
            "reliability",
            fields.get("reliability", ""),
            "Document source must have a reliability level",
            errors,
        )
        validate_enum(fields.get("reliability", ""), RELIABILITY_LEVELS, "reliability", errors)

    if entry_type == "investigation_event":
        _required("date", fields.get("date", ""), "Investigation event must have a date", errors)

    if entry_type == "transaction":
        _required("date", fields.get("date", ""), "Transaction must have a date", errors)
        txn_type = fields.get("transaction_type", "")
        validate_enum(txn_type, TRANSACTION_TYPES, "transaction_type", errors)
        if txn_type in ("payment", "bribe", "kickback") and not fields.get("amount", ""):
            errors.append(
                {
                    "field": "amount",
                    "rule": "required",
                    "message": f"Transaction of type '{txn_type}' must have an amount",
                }
            )
        _required("sender", fields.get("sender", ""), "Transaction must have a sender", errors)
        _required(
            "receiver", fields.get("receiver", ""), "Transaction must have a receiver", errors
        )

    if entry_type == "legal_action":
        _required("date", fields.get("date", ""), "Legal action must have a date", errors)
        _required(
            "case_type", fields.get("case_type", ""), "Legal action must have a case_type", errors
        )
        validate_enum(fields.get("case_type", ""), CASE_TYPES, "case_type", errors)
        _required(
            "jurisdiction",
            fields.get("jurisdiction", ""),
            "Legal action must have a jurisdiction",
            errors,
        )
        validate_enum(fields.get("case_status", ""), CASE_STATUSES, "case_status", errors)

    if entry_type == "ownership":
        _required("owner", fields.get("owner", ""), "Ownership must have an owner", errors)
        _required("asset", fields.get("asset", ""), "Ownership must have an asset", errors)

    if entry_type == "membership":
        _required("person", fields.get("person", ""), "Membership must have a person", errors)
        _required(
            "organization",
            fields.get("organization", ""),
            "Membership must have an organization",
            errors,
        )

    if entry_type == "funding":
        _required("funder", fields.get("funder", ""), "Funding must have a funder", errors)
        _required("recipient", fields.get("recipient", ""), "Funding must have a recipient", errors)
        validate_enum(fields.get("mechanism", ""), FUNDING_MECHANISMS, "mechanism", errors)

    if entry_type == "evidence":
        _required(
            "evidence_type",
            fields.get("evidence_type", ""),
            "Evidence must have an evidence_type",
            errors,
        )
        validate_enum(fields.get("evidence_type", ""), EVIDENCE_TYPES, "evidence_type", errors)

    if entry_type == "claim":
        _required("assertion", fields.get("assertion", ""), "Claim must have an assertion", errors)
        validate_enum(fields.get("claim_status", ""), CLAIM_STATUSES, "claim_status", errors)
        validate_enum(fields.get("confidence", ""), CONFIDENCE_LEVELS, "confidence", errors)

    importance = fields.get("importance")
    if importance is not None and isinstance(importance, int):
        if importance < 1 or importance > 10:
            errors.append(
                {
                    "field": "importance",
                    "message": f"Importance must be 1-10, got: {importance}",
                }
            )

    return errors
