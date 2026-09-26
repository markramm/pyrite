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
- CLI: what `pyrite/cli/entry_commands.py`'s real write commands (`create`,
  `add`, `update`, `delete`, `link`) actually dispatch to today -- NOT
  `pyrite.utils.errors.cli_error_from` (ADR-0037 theme 2 added that
  function, but no CLI call site has adopted it yet; characterizing it
  here would pin aspirational behaviour, not the real CLI -- exactly the
  mistake the conductor's cold read of #501 caught). Every one of these
  commands catches `ValidationError` first and routes it to
  `_refusal_exit` (`exc.error_code`, a `declared_types`-aware suggestion
  swap), then falls through to a bare
  `except (PyriteError, ValueError) as e: _cli_error(str(e), "rich")` for
  everything else -- which does NOT read `error_code` (defaults to the
  literal `"ERROR"`) and does NOT read `public_message` (uses `str(e)`
  directly). `cli_body` below replicates that two-branch dispatch by
  class, not `cli_error_from`'s uniform mapping.

  `EntryNotFoundError`/`KBNotFoundError` are a partial, in-flight
  exception: PR #502 (open, not merged as of this theme) adds explicit
  catches for those two ahead of the generic one, emitting hardcoded
  `"NOT_FOUND"`/`"KB_NOT_FOUND"` literals -- not `exc.error_code` either.
  This harness characterizes current `dev` (#502 unmerged), so those two
  classes still fall through the generic branch here; when #502 merges,
  `_CLI_DISPATCH`'s comment below says what to add, and the goldens need a
  reviewed update, not a silent regenerate.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

import pyrite.exceptions as exc_module
from pyrite.exceptions import PyriteError, ValidationError
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
    """The `--format json` payload `pyrite create`/`add`/`update`/`delete`/
    `link` actually print today, replicated by class -- not `cli_error_from`
    (module docstring above explains why: no call site uses it yet).

    Two branches, matching `entry_commands.py`'s real `try/except` order:

    - `ValidationError` (and every subclass) -> `_refusal_exit`'s shape:
      `exc.error_code` (never the `"VALIDATION_FAILED"` literal fallback in
      its source -- that fallback is unreachable now that every class has
      its own code, but kept there for a non-`PyriteError` caller), and a
      `declared_types`-aware suggestion swap (`UndeclaredTypeError` only).
    - Everything else -> the generic `except (PyriteError, ValueError) as e:
      _cli_error(str(e), "rich")`: code `"ERROR"` (the literal default,
      `error_code` never passed), message `str(e)` (`public_message` is
      never consulted at this site), no suggestion, not retryable.
    """
    if isinstance(exc, ValidationError):
        suggestion = getattr(exc, "suggestion", None)
        if getattr(exc, "declared_types", None) is not None:
            suggestion = (
                "Use `pyrite kb schema show <kb>` to inspect the declared types, or pass "
                "--allow-undeclared to override."
            )
        return build_error(
            str(exc),
            exc.error_code,
            suggestion=suggestion,
            retryable=False,
        )
    return build_error(str(exc), "ERROR")


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
