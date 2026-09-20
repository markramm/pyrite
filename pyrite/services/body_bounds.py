"""Bounds on how much body text one agent-facing read may return.

ADR-0034, "Agent-facing reads are bounded by default". Three numbers, each
read from the environment at server start and each validated there rather
than silently falling back:

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
entries were asked for.

This module owns the numbers and the arithmetic so that the MCP server, and
later the CLI (ADR-0034 rule 5) and REST (rule 6), share one implementation
rather than reaching into each other.
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

#: Keys a truncated body always carries. ADR-0034 rule 2: truncation is never
#: silent, and a `fields` projection keeps these — a caller handed a slice with
#: no marker cannot tell it was truncated, and may write it back.
MARKER_KEYS: tuple[str, ...] = (
    "body_truncated",
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
