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


def _register_db_kbs(config: PyriteConfig, db: PyriteDB) -> None:
    """Merge DB-registered KBs (from 'pyrite kb add') into config.

    This ensures all code paths see user-added KBs, not just the registry service.
    Config.yaml KBs take precedence (skipped if name already exists).
    """
    try:
        from sqlalchemy import text

        rows = db.session.execute(
            text("SELECT name, path, kb_type, description FROM kb WHERE source = 'user'")
        ).fetchall()
        if rows:
            db_kbs = [
                {"name": r[0], "path": r[1], "kb_type": r[2], "description": r[3] or ""}
                for r in rows
            ]
            added = config.register_db_kbs(db_kbs)
            if added:
                logger.debug("Merged %d DB-registered KBs into config", added)
    except Exception:
        logger.debug("Could not merge DB KBs (table may not exist yet)", exc_info=True)


def _init_base() -> tuple[PyriteConfig, PyriteDB, KBService]:
    """Shared construction for all CLI context managers."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    _register_db_kbs(config, db)
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
    try:
        yield config, db
    finally:
        db.close()


def get_config_and_db() -> tuple[PyriteConfig, PyriteDB]:
    """Get config and db without a context manager.

    Note: callers are responsible for calling db.close(). Prefer cli_db_context()
    for new code.
    """
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    return config, db
