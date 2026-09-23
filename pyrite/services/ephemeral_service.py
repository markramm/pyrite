"""
Ephemeral KB Service

Lifecycle management for temporary knowledge bases with TTL.
"""

import logging
import re
import shutil
import time
from pathlib import Path

from ..config import KBConfig, PyriteConfig, save_config
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)

# An ephemeral KB's name becomes a directory under <workspace>/ephemeral/ and
# is chosen by any write-role user, so it must be a plain name: no separators,
# no dot segments, not absolute.
_EPHEMERAL_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


class InvalidEphemeralKBNameError(ValueError):
    """The requested ephemeral KB name is unsafe or already in use."""


class EphemeralKBService:
    """Service for ephemeral KB lifecycle management."""

    def __init__(self, config: PyriteConfig, db: PyriteDB):
        self.config = config
        self.db = db

    def create_ephemeral_kb(self, name: str, ttl: int = 3600, description: str = "") -> KBConfig:
        """Create an ephemeral KB with TTL.

        Raises InvalidEphemeralKBNameError for a name that is not a plain
        name, that another KB uses (in config or in the registry table), or
        whose directory already exists. The directory is created with
        exist_ok=False, so it is the claim: of two concurrent creates of one
        name, or of two names one case-insensitive filesystem folds together,
        exactly one gets it, and a leftover directory is never adopted.
        """
        if not isinstance(name, str) or not _EPHEMERAL_NAME_RE.fullmatch(name):
            raise InvalidEphemeralKBNameError(
                "Invalid ephemeral KB name: use 1-64 letters, digits, '-' or '_', "
                "starting with a letter or digit"
            )
        if self._name_in_use(name):
            raise InvalidEphemeralKBNameError("That KB name is not available")
        ephemeral_dir = self._root() / name
        if not self._inside_root(ephemeral_dir):
            raise InvalidEphemeralKBNameError("Invalid ephemeral KB name")
        self._root().mkdir(parents=True, exist_ok=True)
        try:
            ephemeral_dir.mkdir(exist_ok=False)
        except FileExistsError:
            raise InvalidEphemeralKBNameError("That KB name is not available") from None

        try:
            return self._register(name, ephemeral_dir, ttl, description)
        except BaseException:
            # The directory is ours (we just created it); do not leave a
            # leftover that would block the name forever.
            shutil.rmtree(ephemeral_dir, ignore_errors=True)
            raise

    def _name_in_use(self, name: str) -> bool:
        """True when config or the KB registry table already has this name."""
        if self.config.get_kb(name) is not None:
            return True
        rows = self.db.execute_sql("SELECT 1 FROM kb WHERE name = :name", {"name": name})
        return bool(rows)

    def _register(self, name: str, ephemeral_dir: Path, ttl: int, description: str) -> KBConfig:
        description = description or f"Ephemeral KB (TTL: {ttl}s)"
        # Insert-only: another process may have registered the name since the
        # check above, and that row must not be overwritten.
        if not self.db.insert_new_kb(
            name=name, kb_type="generic", path=str(ephemeral_dir), description=description
        ):
            raise InvalidEphemeralKBNameError("That KB name is not available")
        kb = KBConfig(
            name=name,
            path=ephemeral_dir,
            kb_type="generic",
            description=description,
            ephemeral=True,
            ttl=ttl,
            created_at_ts=time.time(),
        )
        try:
            self.config.add_kb(kb)
            save_config(self.config)
        except BaseException:
            if self.config.get_kb(name) is kb:
                self.config.remove_kb(name)
            self.db.unregister_kb(name)
            raise
        return kb

    def _root(self) -> Path:
        return self.config.settings.workspace_path / "ephemeral"

    def _inside_root(self, path: Path) -> bool:
        """True when path resolves strictly inside the ephemeral root."""
        root = self._root().resolve()
        resolved = Path(path).resolve()
        return resolved != root and resolved.is_relative_to(root)

    def _remove_dir(self, kb: KBConfig) -> None:
        """Delete an expired KB's directory -- only ever inside the ephemeral root.

        A KB persisted to config before names were validated can point at any
        directory (another KB's, say); expiring it must not delete that.
        """
        if not kb.path.exists():
            return
        if not self._inside_root(kb.path):
            logger.warning(
                "Ephemeral KB %r points outside %s; unregistering it without deleting %s",
                kb.name,
                self._root(),
                kb.path,
            )
            return
        shutil.rmtree(kb.path, ignore_errors=True)

    def list_ephemeral_kbs(self) -> list[dict]:
        """List all active ephemeral KBs with metadata."""
        now = time.time()
        result = []
        for kb in self.config.knowledge_bases:
            if not kb.ephemeral:
                continue
            expires_at = (kb.created_at_ts + kb.ttl) if kb.created_at_ts and kb.ttl else None
            result.append(
                {
                    "name": kb.name,
                    "path": str(kb.path),
                    "created_at": kb.created_at_ts,
                    "ttl": kb.ttl,
                    "expires_at": expires_at,
                    "expired": expires_at is not None and now > expires_at,
                }
            )
        return result

    def _remove(self, kb: KBConfig) -> None:
        """Remove an ephemeral KB: its index rows, its grants, its files, its config.

        The per-KB grants go too. `AuthService.create_user_ephemeral_kb`
        records an admin grant for the creator, and a grant left behind is
        inherited by the next KB registered under the same name. Does not
        save the config; callers do, once.
        """
        from .auth_service import AuthService

        self.db.unregister_kb(kb.name)
        AuthService(self.db, self.config.settings.auth).revoke_all_kb_permissions(kb.name)
        # Never outside the ephemeral root (see _remove_dir).
        self._remove_dir(kb)
        self.config.remove_kb(kb.name)

    def force_expire_kb(self, name: str) -> bool:
        """Force-expire a specific ephemeral KB. Returns True if removed."""
        kb = next((k for k in self.config.knowledge_bases if k.name == name), None)
        if not kb or not kb.ephemeral:
            return False
        self._remove(kb)
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
                self._remove(kb)
                removed.append(kb.name)

        if removed:
            save_config(self.config)

        return removed
