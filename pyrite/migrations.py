"""
Schema Migration Registry

Provides decorator-based migration registration and chain execution.
Migrations transform raw frontmatter dicts between schema versions.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    entry_type: str
    from_version: int
    to_version: int
    fn: Callable[[dict], dict]
    description: str = ""


class MigrationRegistry:
    def __init__(self):
        self._migrations: dict[str, list[Migration]] = defaultdict(list)

    def register(self, entry_type: str, from_version: int, to_version: int, description: str = ""):
        """Decorator to register a migration function."""
        def decorator(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
            self.add(Migration(
                entry_type=entry_type,
                from_version=from_version,
                to_version=to_version,
                fn=fn,
                description=description,
            ))
            return fn
        return decorator

    def add(self, migration: Migration) -> None:
        self._migrations[migration.entry_type].append(migration)

    def get_chain(self, entry_type: str, from_version: int, to_version: int) -> list[Migration]:
        """Get ordered migration chain from from_version to to_version.

        Raises ValueError if there are gaps in the chain.
        """
        if from_version >= to_version:
            return []

        available = sorted(
            [m for m in self._migrations.get(entry_type, [])
             if m.from_version >= from_version and m.to_version <= to_version],
            key=lambda m: m.from_version,
        )

        chain = []
        current = from_version
        for m in available:
            if m.from_version == current:
                chain.append(m)
                current = m.to_version

        if current != to_version:
            raise ValueError(
                f"Migration gap for '{entry_type}': cannot reach version {to_version} "
                f"from {from_version} (stuck at {current})"
            )

        return chain

    def apply(self, entry_type: str, data: dict, from_version: int, to_version: int) -> dict:
        """Apply migration chain to a frontmatter dict."""
        chain = self.get_chain(entry_type, from_version, to_version)
        for migration in chain:
            data = migration.fn(data)
            data["_schema_version"] = migration.to_version
        return data

    def has_migrations(self, entry_type: str) -> bool:
        return bool(self._migrations.get(entry_type))


# Global singleton
_registry: MigrationRegistry | None = None
_plugins_loaded = False


def get_migration_registry() -> MigrationRegistry:
    global _registry
    if _registry is None:
        _registry = MigrationRegistry()
    return _registry


def load_plugin_migrations() -> None:
    """Load migrations from all plugins (called once, lazily)."""
    global _plugins_loaded
    if _plugins_loaded:
        return
    _plugins_loaded = True

    registry = get_migration_registry()
    try:
        from .plugins import get_registry as get_plugin_registry

        for migration_dict in get_plugin_registry().get_all_migrations():
            registry.add(Migration(
                entry_type=migration_dict["entry_type"],
                from_version=migration_dict["from_version"],
                to_version=migration_dict["to_version"],
                fn=migration_dict["fn"],
                description=migration_dict.get("description", ""),
            ))
    except Exception:
        logger.warning("Failed to load plugin migrations", exc_info=True)
