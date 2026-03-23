"""
KB Registry Service — DB-first unified KB lifecycle management.

All surfaces (CLI, REST API, MCP, Web UI) delegate KB CRUD here.
Config.yaml KBs are seeded as source="config"; user-added KBs are source="user".
"""

import logging
from pathlib import Path
from typing import Any

from ..config import KBConfig, PyriteConfig
from ..exceptions import KBNotFoundError, KBProtectedError
from ..storage.database import PyriteDB
from ..storage.index import IndexManager

logger = logging.getLogger(__name__)


class KBRegistryService:
    """Unified KB registry backed by the DB kb table."""

    def __init__(self, config: PyriteConfig, db: PyriteDB, index_mgr: IndexManager):
        self.config = config
        self.db = db
        self.index_mgr = index_mgr

    def seed_from_config(self) -> int:
        """Upsert config.yaml KBs into DB with source='config'. Idempotent.

        Returns the number of KBs seeded.
        """
        count = 0
        for kb in self.config.knowledge_bases:
            self.db.register_kb(
                name=kb.name,
                kb_type=kb.kb_type,
                path=str(kb.path),
                description=kb.description,
                source="config",
                default_role=kb.default_role,
            )
            count += 1
        return count

    def list_kbs(self, type_filter: str | None = None) -> list[dict[str, Any]]:
        """List all KBs from DB, enriched with config metadata."""
        from sqlalchemy import text

        query = "SELECT * FROM kb ORDER BY name"
        rows = self.db.session.execute(text(query)).fetchall()

        result = []
        for row in rows:
            r = dict(row._mapping)
            # Enrich with config metadata (read_only, shortname, etc.)
            cfg = self.config.get_kb(r["name"])
            kb_info = {
                "name": r["name"],
                "type": r.get("kb_type", "generic"),
                "path": r.get("path", ""),
                "description": r.get("description", ""),
                "source": r.get("source", "user"),
                "read_only": cfg.read_only if cfg else False,
                "shortname": cfg.shortname if cfg else None,
                "entries": r.get("entry_count", 0) or 0,
                "indexed": bool(r.get("last_indexed")),
                "last_indexed": r.get("last_indexed"),
                "default_role": r.get("default_role"),
            }
            if type_filter and kb_info["type"] != type_filter:
                continue
            result.append(kb_info)
        return result

    def get_kb(self, name: str) -> dict[str, Any] | None:
        """Get a single KB from DB."""
        from ..storage.models import KB

        kb = self.db.session.get(KB, name)
        if not kb:
            return None
        cfg = self.config.get_kb(name)
        return {
            "name": kb.name,
            "type": kb.kb_type,
            "path": kb.path,
            "description": kb.description or "",
            "source": kb.source or "user",
            "read_only": cfg.read_only if cfg else False,
            "shortname": cfg.shortname if cfg else None,
            "entries": kb.entry_count or 0,
            "indexed": bool(kb.last_indexed),
            "last_indexed": kb.last_indexed,
            "default_role": kb.default_role,
        }

    def add_kb(
        self,
        name: str,
        path: str,
        kb_type: str = "generic",
        description: str = "",
    ) -> dict[str, Any]:
        """Register a new user KB in the DB (not config.yaml).

        Raises ValueError if a KB with the same name already exists.
        """
        from ..storage.models import KB

        existing = self.db.session.get(KB, name)
        if existing:
            raise ValueError(f"KB '{name}' already exists")

        resolved = Path(path).expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)

        self.db.register_kb(
            name=name,
            kb_type=kb_type,
            path=str(resolved),
            description=description,
            source="user",
        )
        return self.get_kb(name)  # type: ignore[return-value]

    def remove_kb(self, name: str) -> bool:
        """Remove a user-added KB. Raises KBProtectedError for config KBs."""
        from ..storage.models import KB

        kb = self.db.session.get(KB, name)
        if not kb:
            raise KBNotFoundError(f"KB '{name}' not found")

        if (kb.source or "user") == "config":
            raise KBProtectedError(
                f"KB '{name}' is defined in config.yaml and cannot be removed via the registry. "
                "Edit config.yaml to remove it."
            )

        self.db.unregister_kb(name)
        return True

    def update_kb(self, name: str, **updates: Any) -> dict[str, Any]:
        """Update KB metadata (description, kb_type)."""
        from ..storage.models import KB

        kb = self.db.session.get(KB, name)
        if not kb:
            raise KBNotFoundError(f"KB '{name}' not found")

        allowed = {"description", "kb_type", "default_role"}
        for key, value in updates.items():
            if key in allowed:
                setattr(kb, key, value)
        self.db.session.commit()
        return self.get_kb(name)  # type: ignore[return-value]

    def reindex_kb(self, name: str) -> dict[str, int]:
        """Reindex a specific KB. Works for both config and user KBs."""
        # Try config first
        kb_config = self.config.get_kb(name)
        if kb_config:
            return self.index_mgr.sync_kb(kb_config)

        # Fall back to DB-only KB
        kb_config = self.get_kb_config(name)
        if not kb_config:
            raise KBNotFoundError(f"KB '{name}' not found")
        return self.index_mgr.sync_kb(kb_config)

    def health_kb(self, name: str) -> dict[str, Any]:
        """Check KB health: path exists, file count vs index count, staleness."""
        from ..storage.models import KB

        kb = self.db.session.get(KB, name)
        if not kb:
            raise KBNotFoundError(f"KB '{name}' not found")

        kb_path = Path(kb.path)
        path_exists = kb_path.exists()

        file_count = 0
        if path_exists:
            file_count = sum(
                1 for f in kb_path.rglob("*.md") if not any(p.startswith(".") for p in f.parts)
            )

        entry_count = kb.entry_count or 0
        healthy = path_exists and abs(file_count - entry_count) <= max(1, entry_count * 0.1)

        return {
            "name": name,
            "healthy": healthy,
            "path_exists": path_exists,
            "path": kb.path,
            "file_count": file_count,
            "entry_count": entry_count,
            "last_indexed": kb.last_indexed,
            "source": kb.source or "user",
        }

    def get_kb_config(self, name: str) -> KBConfig | None:
        """Build a KBConfig from a DB row (for DB-only KBs)."""
        # Try config first
        cfg = self.config.get_kb(name)
        if cfg:
            return cfg

        # Build from DB row
        from ..storage.models import KB

        kb = self.db.session.get(KB, name)
        if not kb:
            return None

        return KBConfig(
            name=kb.name,
            path=Path(kb.path),
            kb_type=kb.kb_type or "generic",
            description=kb.description or "",
            default_role=kb.default_role,
        )
