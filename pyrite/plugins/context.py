"""
Plugin Context

Provides shared dependencies to plugins, replacing per-handler self-bootstrapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config import PyriteConfig
    from ..schema import KBSchema
    from ..storage.database import PyriteDB


@dataclass
class PluginContext:
    """Shared context for plugin operations.

    Provides config, db, and request-scoped metadata to plugins,
    eliminating the need for each handler to call load_config()/PyriteDB().

    Supports dict-style access for backwards compatibility with hook context dicts.
    """

    config: PyriteConfig
    db: PyriteDB
    kb_name: str = ""
    user: str = ""
    operation: str = ""
    kb_schema: KBSchema | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for backwards compat with hooks expecting context['kb_name']."""
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style .get() for backwards compat."""
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra.get(key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) or key in self.extra
