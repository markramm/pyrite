"""Bounds on body text crossing the agent-facing surfaces (ADR-0034).

Two halves of one rule, kept in one module because the second exists only to
catch what the first emits.

**Reads are bounded** (rules 1, 3). Three numbers, each read from the
environment at server start and each validated there rather than silently
falling back:

===========================  =======  ====================================
``PYRITE_BODY_CHUNK_DEFAULT``   8000  chunk returned when the caller named
                                      no ``body_limit``
``PYRITE_BODY_CHUNK_MAX``      20000  per-body ceiling; clamps whatever
                                      ``body_limit`` the caller asked for
``PYRITE_BODY_RESPONSE_BUDGET``40000  total body characters one response
                                      may carry across all of its entries
===========================  =======  ====================================

The per-body ceiling alone does not bound a response: fifty entries at the
ceiling is a megabyte. :meth:`BodyBounds.fill_budget` spends the response
budget in request order, so a multi-entry read is bounded no matter how many
entries were asked for. A bounded body always carries :data:`MARKER_KEYS`.

**A bounded body is never valid input to a write** (rule 2). The marker the
read side attaches is what the write side refuses: an agent that edits the
chunk it was handed and saves it would replace the whole stored body with
that fragment -- silent, permanent, and produced by the safety feature
itself. :func:`refuse_truncated_body` is the one implementation of that
refusal; every write surface (MCP, REST, CLI) calls it on the **raw**
request, before any model drops the undeclared key and before the service
layer, which takes an ``Entry`` and cannot carry the marker.

Keeping both halves here is what stops them drifting: the keys the read side
attaches and the keys the write side refuses are the same tuple, named once.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from ..exceptions import ConfigError

DEFAULT_BODY_CHUNK = 8000
MAX_BODY_CHUNK = 20_000
BODY_RESPONSE_BUDGET = 40_000

ENV_DEFAULT_CHUNK = "PYRITE_BODY_CHUNK_DEFAULT"
ENV_MAX_CHUNK = "PYRITE_BODY_CHUNK_MAX"
ENV_RESPONSE_BUDGET = "PYRITE_BODY_RESPONSE_BUDGET"

#: The one key that says "this body is a fragment". Truthy on a write means
#: refuse (:func:`refuse_truncated_body`); absent means nothing was withheld.
TRUNCATION_MARKER = "body_truncated"

#: Keys a truncated body always carries. ADR-0034 rule 2: truncation is never
#: silent, and a `fields` projection keeps these — a caller handed a slice with
#: no marker cannot tell it was truncated, and may write it back.
#:
#: The read side attaches them; the write side refuses on the first and strips
#: all four before storing, because they are read transport and never entry
#: content. One tuple, so the two halves cannot disagree about the spelling.
MARKER_KEYS: tuple[str, ...] = (
    TRUNCATION_MARKER,
    "body_length",
    "body_offset",
    "body_chunk_size",
)


def _read_positive_int(name: str, default: int) -> int:
    """Read ``name`` from the environment as a positive integer.

    Unset (or empty after stripping) falls back to ``default``. Anything else
    that is not a positive integer raises :class:`ConfigError`: ADR-0034 rule
    4 requires invalid values to fail loudly at start, because a deployment
    that silently ignores its own tuning is worse than one that will not boot.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    text = raw.strip()
    if not text:
        raise ConfigError(
            f"{name}={raw!r} is not a positive integer (unset it to use the default of {default})"
        )
    try:
        value = int(text)
    except ValueError:
        raise ConfigError(
            f"{name}={raw!r} is not a positive integer (unset it to use the default of {default})"
        ) from None
    if value <= 0:
        raise ConfigError(
            f"{name}={raw!r} must be greater than 0 (unset it to use the default of {default})"
        )
    return value


@dataclass(frozen=True)
class BodyBounds:
    """The loaded, validated body bounds for one server instance."""

    default_chunk: int = DEFAULT_BODY_CHUNK
    max_chunk: int = MAX_BODY_CHUNK
    response_budget: int = BODY_RESPONSE_BUDGET

    def __post_init__(self) -> None:
        if self.default_chunk > self.max_chunk:
            raise ConfigError(
                f"{ENV_DEFAULT_CHUNK}={self.default_chunk} is greater than "
                f"{ENV_MAX_CHUNK}={self.max_chunk}: the default chunk cannot "
                "exceed the per-body ceiling"
            )

    # -- per body ---------------------------------------------------------

    def effective_limit(self, limit: int | None = None) -> int:
        """The per-body limit actually applied for a caller's ``body_limit``.

        ``None`` (not passed) means the default chunk; anything else is
        clamped to the ceiling and floored at zero. ADR-0034 rule 1: a
        parameter that reduces output never *raises* a bound.
        """
        if limit is None:
            return self.default_chunk
        return max(0, min(int(limit), self.max_chunk))

    def chunk_body(
        self,
        entry: dict[str, Any],
        offset: int = 0,
        limit: int | None = None,
        budget: int | None = None,
    ) -> dict[str, Any]:
        """Return ``entry`` with its body bounded, marked when truncated.

        The body is sliced to ``[offset : offset + n]`` where ``n`` is the
        effective limit, further reduced by ``budget`` when a response budget
        is being spent. An entry whose body arrives whole from offset 0 is
        returned unchanged and carries no marker keys — a caller can test for
        ``body_truncated`` rather than comparing lengths.

        ``entry`` is never mutated.
        """
        body = entry.get("body")
        if body is None:
            return entry
        body_len = len(body)
        # A negative offset would slice from the END: `body[-5 : -5 + 10]` is
        # the tail of a short body and EMPTY on a long one, either way
        # reported as a read from `body_offset: -5`. Clamp it, so an offset
        # always means "characters from the start".
        offset = max(0, int(offset))
        limit = self.effective_limit(limit)
        if budget is not None:
            limit = min(limit, max(0, budget))
        chunk = body[offset : offset + limit] if limit > 0 else ""
        if offset == 0 and len(chunk) == body_len:
            # Whole body, nothing withheld: no marker (an empty body lands
            # here too, so a zero-budget empty body is not reported truncated).
            return entry
        return {
            **entry,
            "body": chunk,
            "body_truncated": True,
            "body_length": body_len,
            "body_offset": offset,
            "body_chunk_size": len(chunk),
        }

    # -- per response -----------------------------------------------------

    def fill_budget(
        self,
        entries: list[dict[str, Any]],
        offset: int = 0,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Bound a list of entries by the per-response budget.

        Bodies are filled in request order. Each entry takes at most the
        effective per-body limit and at most what remains of the budget; an
        entry that arrives after the budget is spent comes back with an empty
        body **and the marker**, carrying its true ``body_length`` — it is not
        dropped and not reported as not-found, so the caller can see there was
        more and continue with ``kb_read_body``.

        Entries with no body, or a ``None`` or empty body, spend nothing.
        """
        remaining = self.response_budget
        out: list[dict[str, Any]] = []
        for entry in entries:
            bounded = self.chunk_body(entry, offset=offset, limit=limit, budget=remaining)
            remaining -= len(bounded.get("body") or "")
            out.append(bounded)
        return out


def load_body_bounds() -> BodyBounds:
    """Load the body bounds from the environment, failing loudly if invalid."""
    return BodyBounds(
        default_chunk=_read_positive_int(ENV_DEFAULT_CHUNK, DEFAULT_BODY_CHUNK),
        max_chunk=_read_positive_int(ENV_MAX_CHUNK, MAX_BODY_CHUNK),
        response_budget=_read_positive_int(ENV_RESPONSE_BUDGET, BODY_RESPONSE_BUDGET),
    )


REFUSAL_CODE = "VALIDATION_FAILED"

REFUSAL_MESSAGE = (
    "Refusing to write a body marked body_truncated: the body you are writing "
    "is a partial read, and writing it would replace the stored entry with that "
    "fragment (ADR-0034). Re-read the whole body first -- kb_read_body with "
    "body_offset paging until has_more is false, or a body_limit above "
    "body_length -- then write that, without the body_truncated key."
)

REFUSAL_SUGGESTION = (
    "Call kb_read_body (or pass a large enough body_limit) to assemble the full "
    "body, then retry the write with the complete text and no body_truncated key. "
    "To change other fields without touching the body, omit body from the request."
)


def _is_truthy_marker(value: Any) -> bool:
    """Is this value a `body_truncated` that means "yes, truncated"?

    `True` and the strings a JSON-ish client might send in its place count.
    `False`, `None`, `0` and the string `"false"` do not: a read that did not
    truncate carries `body_truncated: false`, and refusing that would break
    every caller that faithfully echoes back what it was given.
    """
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return bool(value)


def carries_truncation_marker(payload: Any) -> bool:
    """Does `payload` carry a truthy `body_truncated`, at any depth?

    Top level is the documented shape. `metadata` (MCP) and the extension
    bag it becomes are searched too: a caller that relays a read result into
    a metadata dict is doing the same dangerous thing one level down, and
    ADR-0034's rule is about the body, not about where the key sits.
    """
    if isinstance(payload, dict):
        if TRUNCATION_MARKER in payload and _is_truthy_marker(payload[TRUNCATION_MARKER]):
            return True
        return any(carries_truncation_marker(v) for v in payload.values())
    if isinstance(payload, (list, tuple)):
        return any(carries_truncation_marker(v) for v in payload)
    return False


def has_body(payload: Any, *, body_key: str = "body") -> bool:
    """Is this write actually writing a body, at the top level or nested?

    A metadata-only update that happens to carry the marker writes nothing
    truncated, so it is allowed: the refusal protects bodies, and there is no
    body here to lose. Nested shapes count because some write tools carry
    their bodies one level down (a list of child-task specs, an import's
    parsed entries).

    The test is ``is not None``, deliberately, **not** truthiness. An entry
    that :meth:`BodyBounds.fill_budget` reached after the per-response budget
    was spent comes back with ``body: ""`` and the full marker; that empty
    string is the most destructive thing on this branch to write back, since
    it replaces a whole stored body with nothing. ``""`` is a body.
    """
    if isinstance(payload, dict):
        if payload.get(body_key) is not None:
            return True
        return any(has_body(v, body_key=body_key) for v in payload.values())
    if isinstance(payload, (list, tuple)):
        return any(has_body(v, body_key=body_key) for v in payload)
    return False


def refuse_truncated_body(payload: Any, *, body_key: str = "body") -> str | None:
    """Return the refusal message if this write must be refused, else `None`.

    A write is refused when it carries **both** a body and a truthy
    `body_truncated` marker. Callers turn the message into their surface's own
    error shape: MCP's flat `{"error", "error_code", "retryable"}` envelope, or
    REST's structured `detail` -- with `retryable` false either way, because the
    same truncated body fails identically on every retry.
    """
    if not has_body(payload, body_key=body_key):
        return None
    if not carries_truncation_marker(payload):
        return None
    return REFUSAL_MESSAGE
