"""
Ephemeral KB Service

Lifecycle management for temporary knowledge bases with TTL.
"""

import logging
import shutil
import time

from ..config import KBConfig, PyriteConfig, save_config
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


class EphemeralKBService:
    """Service for ephemeral KB lifecycle management."""

    def __init__(self, config: PyriteConfig, db: PyriteDB):
        self.config = config
        self.db = db

    def create_ephemeral_kb(self, name: str, ttl: int = 3600, description: str = "") -> KBConfig:
        """Create an ephemeral KB with TTL."""
        # Create temp directory for ephemeral KB
        ephemeral_dir = self.config.settings.workspace_path / "ephemeral" / name
        ephemeral_dir.mkdir(parents=True, exist_ok=True)

        kb = KBConfig(
            name=name,
            path=ephemeral_dir,
            kb_type="generic",
            description=description or f"Ephemeral KB (TTL: {ttl}s)",
            ephemeral=True,
            ttl=ttl,
            created_at_ts=time.time(),
        )
        self.config.add_kb(kb)
        save_config(self.config)

        # Register in DB
        self.db.register_kb(
            name=name,
            kb_type="generic",
            path=str(ephemeral_dir),
            description=kb.description,
        )

        return kb

    def list_ephemeral_kbs(self) -> list[dict]:
        """List all active ephemeral KBs with metadata."""
        now = time.time()
        result = []
        for kb in self.config.knowledge_bases:
            if not kb.ephemeral:
                continue
            expires_at = (kb.created_at_ts + kb.ttl) if kb.created_at_ts and kb.ttl else None
            result.append({
                "name": kb.name,
                "path": str(kb.path),
                "created_at": kb.created_at_ts,
                "ttl": kb.ttl,
                "expires_at": expires_at,
                "expired": expires_at is not None and now > expires_at,
            })
        return result

    def force_expire_kb(self, name: str) -> bool:
        """Force-expire a specific ephemeral KB. Returns True if removed."""
        kb = next((k for k in self.config.knowledge_bases if k.name == name), None)
        if not kb or not kb.ephemeral:
            return False
        self.db.unregister_kb(kb.name)
        if kb.path.exists():
            shutil.rmtree(kb.path, ignore_errors=True)
        self.config.remove_kb(kb.name)
        save_config(self.config)
        return True

    def gc_ephemeral_kbs(self) -> list[str]:
        """Garbage-collect expired ephemeral KBs. Returns list of removed KB names."""
        removed = []
        now = time.time()

        for kb in list(self.config.knowledge_bases):
            if not kb.ephemeral or not kb.ttl or not kb.created_at_ts:
                continue
            if now - kb.created_at_ts > kb.ttl:
                # Remove from index
                self.db.unregister_kb(kb.name)
                # Remove files
                if kb.path.exists():
                    shutil.rmtree(kb.path, ignore_errors=True)
                # Remove from config
                self.config.remove_kb(kb.name)
                removed.append(kb.name)

        if removed:
            save_config(self.config)

        return removed
