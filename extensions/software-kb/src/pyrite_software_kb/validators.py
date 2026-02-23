"""Software KB validation rules."""

from typing import Any

from .entry_types import (
    ADR_STATUSES,
    BACKLOG_EFFORTS,
    BACKLOG_KINDS,
    BACKLOG_PRIORITIES,
    BACKLOG_STATUSES,
    COMPONENT_KINDS,
    DESIGN_DOC_STATUSES,
    RUNBOOK_KINDS,
    STANDARD_CATEGORIES,
)


def validate_software_kb(
    entry_type: str, data: dict[str, Any], context: dict[str, Any]
) -> list[dict]:
    """Validate software-kb-specific rules."""
    errors: list[dict] = []

    if entry_type == "adr":
        _validate_adr(data, errors)
    elif entry_type == "design_doc":
        _validate_design_doc(data, errors)
    elif entry_type == "standard":
        _validate_standard(data, errors)
    elif entry_type == "component":
        _validate_component(data, errors)
    elif entry_type == "backlog_item":
        _validate_backlog_item(data, errors)
    elif entry_type == "runbook":
        _validate_runbook(data, errors)

    return errors


def _validate_enum(
    data: dict, field: str, allowed: tuple, errors: list[dict], default: str = ""
) -> None:
    value = data.get(field, default)
    if value and value not in allowed:
        errors.append(
            {
                "field": field,
                "rule": "enum",
                "expected": list(allowed),
                "got": value,
            }
        )


def _validate_adr(data: dict[str, Any], errors: list[dict]) -> None:
    _validate_enum(data, "status", ADR_STATUSES, errors, "proposed")

    adr_number = data.get("adr_number")
    if adr_number is not None and adr_number != 0:
        try:
            if int(adr_number) < 1:
                errors.append(
                    {
                        "field": "adr_number",
                        "rule": "min_value",
                        "expected": ">= 1",
                        "got": adr_number,
                    }
                )
        except (TypeError, ValueError):
            errors.append(
                {
                    "field": "adr_number",
                    "rule": "type",
                    "expected": "integer",
                    "got": adr_number,
                }
            )

    status = data.get("status", "proposed")
    if status == "superseded" and not data.get("superseded_by"):
        errors.append(
            {
                "field": "superseded_by",
                "rule": "required_when_superseded",
                "expected": "non-empty superseded_by when status is 'superseded'",
                "got": data.get("superseded_by"),
            }
        )

    if not data.get("date"):
        errors.append(
            {
                "field": "date",
                "rule": "date_recommended",
                "expected": "date for ADR",
                "got": None,
                "severity": "warning",
            }
        )


def _validate_design_doc(data: dict[str, Any], errors: list[dict]) -> None:
    _validate_enum(data, "status", DESIGN_DOC_STATUSES, errors, "draft")


def _validate_standard(data: dict[str, Any], errors: list[dict]) -> None:
    _validate_enum(data, "category", STANDARD_CATEGORIES, errors)


def _validate_component(data: dict[str, Any], errors: list[dict]) -> None:
    _validate_enum(data, "kind", COMPONENT_KINDS, errors)

    if not data.get("path"):
        errors.append(
            {
                "field": "path",
                "rule": "path_recommended",
                "expected": "path linking to code",
                "got": None,
                "severity": "warning",
            }
        )


def _validate_backlog_item(data: dict[str, Any], errors: list[dict]) -> None:
    _validate_enum(data, "kind", BACKLOG_KINDS, errors)
    _validate_enum(data, "status", BACKLOG_STATUSES, errors, "proposed")
    _validate_enum(data, "priority", BACKLOG_PRIORITIES, errors, "medium")

    effort = data.get("effort", "")
    if effort and effort not in BACKLOG_EFFORTS:
        errors.append(
            {
                "field": "effort",
                "rule": "enum",
                "expected": list(BACKLOG_EFFORTS),
                "got": effort,
            }
        )


def _validate_runbook(data: dict[str, Any], errors: list[dict]) -> None:
    _validate_enum(data, "runbook_kind", RUNBOOK_KINDS, errors)
