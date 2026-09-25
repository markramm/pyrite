"""Shared CLI context — eliminates duplicated PyriteDB + service construction."""

import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.exc import SQLAlchemyError

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


def get_config_with_registered_kbs(
    config: PyriteConfig | None = None, *, name: str
) -> PyriteConfig:
    """Resolve a KB from YAML first, then the database registry if necessary.

    Avoid opening the index database when the requested KB is already in
    config.yaml. If registry lookup fails, keep the YAML config usable and let
    the caller report that the requested KB was not found.
    """
    config = config or load_config()
    if config.get_kb(name) is not None:
        return config

    try:
        db = PyriteDB(config.settings.index_path)
        try:
            db.merge_registered_kbs(config)
        finally:
            db.close()
    except (OSError, sqlite3.Error, SQLAlchemyError) as exc:
        logger.warning(
            "Could not read KB registry from index database %s while resolving %r; "
            "using YAML config: %s",
            config.settings.index_path,
            name,
            exc,
        )
    return config
