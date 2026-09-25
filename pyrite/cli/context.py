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
    config, db = get_config_and_db()
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
    config, db = get_config_and_db()
    try:
        yield config, db
    finally:
        db.close()


def get_config_and_db(config: PyriteConfig | None = None) -> tuple[PyriteConfig, PyriteDB]:
    """Get config and db without a context manager, merging DB-registered KBs.

    Pass an already-loaded config when a command owns config loading; otherwise
    this helper loads it. Callers are responsible for calling db.close().
    """
    config = config or load_config()
    db = PyriteDB(config.settings.index_path)
    db.merge_registered_kbs(config)
    return config, db


def get_config_with_registered_kbs(config: PyriteConfig | None = None) -> PyriteConfig:
    """Load or accept a config and merge KBs registered by ``pyrite kb add``.

    Commands that only need KB lookup should use this helper rather than
    opening their own database and duplicating the registry merge.
    """
    config, db = get_config_and_db(config)
    try:
        return config
    finally:
        db.close()
