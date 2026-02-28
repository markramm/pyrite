"""Task validation rules."""

from typing import Any

from .entry_types import TASK_STATUSES


def validate_task(
    entry_type: str, data: dict[str, Any], context: dict[str, Any]
) -> list[dict]:
    """Validate task-specific rules."""
    errors: list[dict] = []

    if entry_type != "task":
        return errors

    _validate_task(data, errors)
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


def _validate_task(data: dict[str, Any], errors: list[dict]) -> None:
    _validate_enum(data, "status", TASK_STATUSES, errors, "open")

    priority = data.get("priority", 5)
    if priority is not None:
        try:
            p = int(priority)
            if p < 1 or p > 10:
                errors.append(
                    {
                        "field": "priority",
                        "rule": "range",
                        "expected": "1-10",
                        "got": priority,
                    }
                )
        except (TypeError, ValueError):
            errors.append(
                {
                    "field": "priority",
                    "rule": "type",
                    "expected": "integer",
                    "got": priority,
                }
            )

    parent = data.get("parent_task")
    if parent is not None and not isinstance(parent, str):
        errors.append(
            {
                "field": "parent_task",
                "rule": "type",
                "expected": "string",
                "got": type(parent).__name__,
            }
        )

    deps = data.get("dependencies")
    if deps is not None and not isinstance(deps, list):
        errors.append(
            {
                "field": "dependencies",
                "rule": "type",
                "expected": "list",
                "got": type(deps).__name__,
            }
        )
