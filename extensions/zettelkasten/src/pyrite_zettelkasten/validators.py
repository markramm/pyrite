"""Zettelkasten validation rules."""

from typing import Any

from .entry_types import MATURITY_LEVELS, PROCESSING_STAGES, ZETTEL_TYPES


def validate_zettel(entry_type: str, data: dict[str, Any], context: dict[str, Any]) -> list[dict]:
    """Validate zettel-specific rules."""
    errors: list[dict] = []

    if entry_type == "zettel":
        zettel_type = data.get("zettel_type", "fleeting")

        # Validate enum values
        if zettel_type not in ZETTEL_TYPES:
            errors.append(
                {
                    "field": "zettel_type",
                    "rule": "enum",
                    "expected": list(ZETTEL_TYPES),
                    "got": zettel_type,
                }
            )

        maturity = data.get("maturity", "seed")
        if maturity and maturity not in MATURITY_LEVELS:
            errors.append(
                {
                    "field": "maturity",
                    "rule": "enum",
                    "expected": list(MATURITY_LEVELS),
                    "got": maturity,
                }
            )

        stage = data.get("processing_stage", "")
        if stage and stage not in PROCESSING_STAGES:
            errors.append(
                {
                    "field": "processing_stage",
                    "rule": "enum",
                    "expected": list(PROCESSING_STAGES),
                    "got": stage,
                }
            )

        # Fleeting notes must have processing_stage
        if zettel_type == "fleeting" and not stage:
            errors.append(
                {
                    "field": "processing_stage",
                    "rule": "required_for_fleeting",
                    "expected": "non-empty processing_stage for fleeting notes",
                    "got": None,
                }
            )

        # Permanent notes should have at least one link (warning)
        if zettel_type == "permanent":
            links = data.get("links", [])
            if not links:
                errors.append(
                    {
                        "field": "links",
                        "rule": "permanent_should_link",
                        "expected": "at least 1 link for permanent notes",
                        "got": 0,
                        "severity": "warning",
                    }
                )

        # Hub notes must have at least 3 outgoing links
        if zettel_type == "hub":
            links = data.get("links", [])
            if len(links) < 3:
                errors.append(
                    {
                        "field": "links",
                        "rule": "hub_min_links",
                        "expected": "at least 3 links for hub notes",
                        "got": len(links),
                    }
                )

    elif entry_type == "literature_note":
        # Literature notes must have source_work
        if not data.get("source_work"):
            errors.append(
                {
                    "field": "source_work",
                    "rule": "required",
                    "expected": "non-empty source_work for literature notes",
                    "got": data.get("source_work"),
                }
            )

    return errors
