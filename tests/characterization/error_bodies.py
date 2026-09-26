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

- REST: `pyrite.server.errors.error_response(exc)` -- the exact
  (status, ``{"detail": {...}}``) pair the registered exception handler
  returns (ADR-0037 theme 2 factored the handler's body out into this
  function precisely so a characterization can call the real logic
  instead of keeping a parallel copy of it in sync by hand).
- MCP: `pyrite.server.mcp_server._refusal(exc)`, called directly -- the
  exact function `_dispatch_tool` calls on every refusal.
- CLI: `pyrite.utils.errors.cli_error_from`'s payload, built the same way
  `cli_error_from` builds it (``exc.public_message or str(exc)``,
  ``exc.error_code`` -- no `legacy_error_code`, which is MCP-only) via
  `build_error`, so this is the exact CLI body without spawning a process
  per class or invoking `typer.Exit`.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

import pyrite.exceptions as exc_module
from pyrite.exceptions import PyriteError
from pyrite.server.errors import error_response
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
    """What the registered exception handler answers for `exc` --
    `pyrite.server.errors.error_response`, the same function
    `register_pyrite_exception_handler`'s handler calls, so this tracks the
    real handler exactly rather than a parallel copy of its table.

    ADR-0037 theme 2: the body is now `{"detail": {"code", "message",
    "retryable", "hint"?}}`, not the old flat `{"code", "message"}` --
    the same wrapper `HTTPException(detail={...})` sites already answered."""
    status_code, content = error_response(exc)
    return {"status": status_code, "body": content}


def mcp_body(exc: PyriteError) -> dict[str, Any]:
    """`_refusal(exc)` -- the exact function `_dispatch_tool` calls."""
    return _refusal(exc)


def cli_body(exc: PyriteError) -> dict[str, Any]:
    """The `--format json` payload `cli_error_from` echoes.

    ADR-0037 theme 2: computed directly from `exc` the same way
    `cli_error_from` does (`exc.public_message or str(exc)`,
    `exc.error_code`), not derived from `mcp_body` -- the CLI carries no
    `legacy_error_code` (that field is MCP-only, for one release, per the
    maintainer's decision of 2026-09-25), so CLI and MCP can now genuinely
    differ in shape for the same exception."""
    message = exc.public_message or str(exc)
    return build_error(
        message,
        exc.error_code,
        suggestion=getattr(exc, "suggestion", None),
        retryable=bool(getattr(exc, "retryable", False)),
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
