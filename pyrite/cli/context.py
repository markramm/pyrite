"""Shared CLI context — eliminates duplicated PyriteDB + service construction."""

from collections.abc import Generator
from contextlib import contextmanager

from ..config import PyriteConfig, load_config
from ..services.kb_service import KBService
from ..storage.database import PyriteDB


@contextmanager
def cli_context() -> Generator[tuple[PyriteConfig, PyriteDB, KBService], None, None]:
    """Provide config, db, and service for CLI commands."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    svc = KBService(config, db)
    try:
        yield config, db, svc
    finally:
        db.close()


def get_config_and_db() -> tuple[PyriteConfig, PyriteDB]:
    """Get config and db without KBService — for commands that only need db access."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    return config, db
