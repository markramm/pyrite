"""One instance of every `PyriteError` subclass, and the body each transport's
real mapping function gives it (ADR-0037 theme 0's error-body acceptance).

This does not drive a live request per class: several classes need elaborate
multi-step setup to reach naturally (`LastAdminError` needs exactly one
admin then a demote attempt; `StorageError` needs a corrupt database), and
theme 0 is a characterization of the **mapping**, not a proof that every
class is reachable from every transport today (that proof, where it's cheap,
lives in `test_error_bodies.py`'s handful of live-request cross-checks
instead). So this module builds one instance of each class directly and
runs it through each transport's own, real, unmodified mapping function:

- REST: `pyrite.server.api._PYRITE_ERROR_STATUS` (the same table the
  registered exception handler walks) plus the same public-message logic
  `register_pyrite_exception_handler`'s `_handler` uses -- reimplemented
  here read-only over the table and the class, not copied by hand, so a
  change to the real handler's classification is what the golden pins, not
  a parallel copy of it.
- MCP: `pyrite.server.mcp_server._refusal(exc)`, called directly -- the
  exact function `_dispatch_tool` calls on every refusal.
- CLI: `pyrite.utils.errors.build_error(message, error_code, ...)`, with the
  same `(message, code, suggestion, retryable)` `_refusal` computed --
  `cli_error`'s JSON-format payload is `build_error`'s return value
  unchanged (see `cli_error`'s source), so this is the exact CLI body
  without spawning a process per class.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

import pyrite.exceptions as exc_module
from pyrite.exceptions import PyriteError
from pyrite.server.api import _PYRITE_ERROR_STATUS
from pyrite.server.mcp_server import _refusal
from pyrite.utils.errors import build_error

# One buildable instance per concrete PyriteError subclass. Most take a
# plain message; a few need required extra fields (see their __init__
# signatures) -- built with the smallest valid value.
_BUILDERS: dict[str, Any] = {
    "UndeclaredTypeError": lambda: exc_module.UndeclaredTypeError(
        "type 'x' is not declared", declared_types=["note", "event"]
    ),
    "SchemaViolationError": lambda: exc_module.SchemaViolationError(
        "schema violation", errors=[{"field": "title", "error": "required"}]
    ),
    "TruncatedBodyError": lambda: exc_module.TruncatedBodyError(
        "body was truncated", suggestion="fetch the full body and retry"
    ),
    "ConfigSaveRefusedError": lambda: exc_module.ConfigSaveRefusedError(
        "config changed on disk", config_file="/config.yaml", dropped=["some-kb"]
    ),
    "ConfigFileUnreadableError": lambda: exc_module.ConfigFileUnreadableError(
        "config file unreadable", config_file="/config.yaml"
    ),
}


def all_pyrite_error_classes() -> list[type[PyriteError]]:
    """Every concrete `PyriteError` subclass in `pyrite.exceptions`, sorted
    by name for a stable golden key order."""
    classes = [
        c
        for _, c in vars(exc_module).items()
        if inspect.isclass(c) and issubclass(c, PyriteError) and c is not PyriteError
    ]
    return sorted(set(classes), key=lambda c: c.__name__)


def build_instance(cls: type[PyriteError]) -> PyriteError:
    builder = _BUILDERS.get(cls.__name__)
    if builder is not None:
        return builder()
    return cls(f"characterization message for {cls.__name__}")


def rest_body(exc: PyriteError) -> dict[str, Any]:
    """What `register_pyrite_exception_handler`'s `_handler` returns for
    `exc` -- reads the same `_PYRITE_ERROR_STATUS` table and the same
    `public_message` rule, so it tracks the real handler exactly."""
    status_code, code = 500, "INTERNAL_ERROR"
    for exc_type, sc, c in _PYRITE_ERROR_STATUS:
        if isinstance(exc, exc_type):
            status_code, code = sc, c
            break
    message = str(exc)
    public_message = getattr(exc, "public_message", None)
    if public_message is not None:
        message = public_message
    return {"status": status_code, "body": {"code": code, "message": message}}


def mcp_body(exc: PyriteError) -> dict[str, Any]:
    """`_refusal(exc)` -- the exact function `_dispatch_tool` calls."""
    return _refusal(exc)


def cli_body(exc: PyriteError) -> dict[str, Any]:
    """The `--format json` payload `cli_error` echoes -- `build_error` with
    the same (message, code, suggestion, retryable) `_refusal` computes, so
    CLI and MCP are characterized from one shared computation, matching
    `pyrite/utils/errors.py`'s documented intent ("errors look the same
    whether they come from the CLI [or] MCP")."""
    mcp = mcp_body(exc)
    return build_error(
        mcp["error"],
        mcp["error_code"],
        suggestion=mcp.get("suggestion"),
        retryable=mcp.get("retryable", False),
    )


@dataclass(frozen=True)
class ErrorBodyCase:
    class_name: str
    rest: dict[str, Any]
    mcp: dict[str, Any]
    cli: dict[str, Any]


def all_error_body_cases() -> list[ErrorBodyCase]:
    cases = []
    for cls in all_pyrite_error_classes():
        exc = build_instance(cls)
        cases.append(
            ErrorBodyCase(
                class_name=cls.__name__,
                rest=rest_body(exc),
                mcp=mcp_body(exc),
                cli=cli_body(exc),
            )
        )
    return cases
