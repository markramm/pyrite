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


def _init_base() -> tuple[PyriteConfig, PyriteDB, KBService]:
    """Shared construction for all CLI context managers."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    db.merge_registered_kbs(config)
    svc = KBService(config, db)
    return config, db, svc


@contextmanager
def cli_context() -> Generator[tuple[PyriteConfig, PyriteDB, KBService], None, None]:
    """Provide config, db, and service for CLI commands."""
    config, db, svc = _init_base()
    try:
        yield config, db, svc
    finally:
        db.close()


@contextmanager
def cli_registry_context() -> Generator[
    tuple[PyriteConfig, PyriteDB, KBService, KBRegistryService], None, None
]:
    """Provide config, db, service, and registry for CLI commands that need KB management."""
    config, db, svc = _init_base()
    index_mgr = IndexManager(db, config)
    registry = KBRegistryService(config, db, index_mgr)
    registry.seed_from_config()
    try:
        yield config, db, svc, registry
    finally:
        db.close()


@contextmanager
def cli_db_context() -> Generator[tuple[PyriteConfig, PyriteDB], None, None]:
    """Provide config and db for commands that only need db access."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    db.merge_registered_kbs(config)
    try:
        yield config, db
    finally:
        db.close()


def get_config_and_db() -> tuple[PyriteConfig, PyriteDB]:
    """Get config and db without a context manager.

    Merges DB-registered KBs (added via ``pyrite kb add``) into the config so
    that commands like ``index sync`` see them — matching ``_init_base()``.
    Without this merge, KBs that live only in the DB (not the YAML config) are
    invisible and indexing them produces 0 entries.

    Note: callers are responsible for calling db.close(). Prefer cli_db_context()
    for new code.
    """
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    db.merge_registered_kbs(config)
    return config, db
