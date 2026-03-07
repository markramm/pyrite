"""Shared CLI context — eliminates duplicated PyriteDB + service construction."""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from ..config import PyriteConfig, load_config
from ..services.kb_registry_service import KBRegistryService
from ..services.kb_service import KBService
from ..storage.database import PyriteDB
from ..storage.index import IndexManager

logger = logging.getLogger(__name__)


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


@contextmanager
def cli_registry_context() -> (
    Generator[tuple[PyriteConfig, PyriteDB, KBService, KBRegistryService], None, None]
):
    """Provide config, db, service, and registry for CLI commands that need KB management."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    svc = KBService(config, db)
    index_mgr = IndexManager(db, config)
    registry = KBRegistryService(config, db, index_mgr)
    registry.seed_from_config()
    try:
        yield config, db, svc, registry
    finally:
        db.close()


def get_config_and_db() -> tuple[PyriteConfig, PyriteDB]:
    """Get config and db without KBService — for commands that only need db access."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    return config, db
