"""Settings service: the instance-wide settings store.

The surfaces read and write settings through this service rather than
reaching ``db.*_setting`` themselves (#380). Presentation rules -- which
keys are secret, who sees them masked -- stay with the surface that shows
them (``server/endpoints/settings_ep.py``); this is the store.
"""

from ..storage.database import PyriteDB


class SettingsService:
    """Read and write instance settings (the ``setting`` table)."""

    def __init__(self, db: PyriteDB):
        self.db = db

    def get(self, key: str) -> str | None:
        """The stored value for ``key``, or ``None`` when it is not set."""
        return self.db.get_setting(key)

    def all(self) -> dict[str, str]:
        """Every stored setting, as ``{key: value}``."""
        return self.db.get_all_settings()

    def set(self, key: str, value: str) -> None:
        """Store ``value`` under ``key``, replacing any earlier value."""
        self.db.set_setting(key, value)

    def delete(self, key: str) -> bool:
        """Remove ``key``. True when a stored setting was removed."""
        return self.db.delete_setting(key)
