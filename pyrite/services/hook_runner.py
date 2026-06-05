"""HookRunner — orchestrates core and plugin lifecycle hooks.

Extracted from KBService so the hook contract (before-raises, after-swallows)
lives in one place rather than being open-coded inside CRUD methods.

## Contract

- ``before_save`` / ``before_delete``: hooks may raise. Any raised exception
  propagates to the caller, aborting persistence. The entry is NOT saved.
- ``after_save`` / ``after_delete``: hook exceptions are logged at WARNING and
  swallowed. The operation is already committed; bubbling an exception here
  would surface a "save failed" error to a caller whose save actually
  succeeded. A failing hook does NOT prevent subsequent hooks from running —
  each after-hook is an independent side effect.

This contract was previously implemented inside ``KBService._run_hooks`` as
a static method. The behavior is preserved exactly; only the home moved.

## Plugin hook dispatch

If a plugin registry is supplied at construction time, ``HookRunner`` will
also run plugin hooks (after the core hooks) under the same contract. Pass
``plugin_registry=None`` to use only core hooks (e.g. in unit tests).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models import Entry
    from ..plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


_BEFORE_HOOK_PREFIX = "before_"


class HookRunner:
    """Run lifecycle hooks with a uniform raise-vs-swallow contract.

    Each instance owns its own ``_core_hooks`` registry, so tests can build
    isolated runners. In production, KBService constructs one runner and
    delegates from every CRUD method.
    """

    def __init__(self, plugin_registry: PluginRegistry | None = None) -> None:
        self._core_hooks: dict[str, list[Callable[..., Any]]] = {}
        self._plugin_registry = plugin_registry

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_core_hook(self, hook_name: str, fn: Callable[..., Any]) -> None:
        """Append a hook function to the named core-hook list.

        Hook functions take ``(entry, context)`` and may return a (possibly
        replaced) entry or ``None``. ``None`` means "no replacement; keep the
        current entry."
        """
        self._core_hooks.setdefault(hook_name, []).append(fn)

    def core_hooks(self, hook_name: str) -> list[Callable[..., Any]]:
        """Return the registered core hooks for a hook name (for inspection)."""
        return list(self._core_hooks.get(hook_name, []))

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def run_before_save(self, entry: Entry, context: dict[str, Any]) -> Entry:
        return self._run("before_save", entry, context)

    def run_after_save(self, entry: Entry, context: dict[str, Any]) -> Entry:
        return self._run("after_save", entry, context)

    def run_before_delete(self, entry: Entry, context: dict[str, Any]) -> Entry:
        return self._run("before_delete", entry, context)

    def run_after_delete(self, entry: Entry, context: dict[str, Any]) -> Entry:
        return self._run("after_delete", entry, context)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run(self, hook_name: str, entry: Entry, context: dict[str, Any]) -> Entry:
        """Run all hooks for ``hook_name`` honoring the raise/swallow contract."""
        is_before = hook_name.startswith(_BEFORE_HOOK_PREFIX)

        # Core hooks first.
        for hook_fn in self._core_hooks.get(hook_name, []):
            try:
                result = hook_fn(entry, context)
                if result is not None:
                    entry = result
            except Exception:
                if is_before:
                    raise
                logger.warning(
                    "Core hook %s failed", getattr(hook_fn, "__name__", repr(hook_fn)),
                    exc_info=True,
                )

        # Plugin hooks second (only if a registry was supplied).
        if self._plugin_registry is None:
            return entry

        try:
            kb_type = context.get("kb_type", "") if context else ""
            return self._plugin_registry.run_hooks_for_kb(
                hook_name, entry, context, kb_type=kb_type,
            )
        except Exception:
            if is_before:
                raise
            logger.warning("Plugin hooks %s failed", hook_name, exc_info=True)
            return entry
