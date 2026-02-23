"""Shared test fixtures for pyrite tests.

Provides composable fixtures for KB setup, database, indexing, and sample data.
Individual test files build on these instead of duplicating setup code.
"""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import EventEntry
from pyrite.models.core_types import PersonEntry
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository


@pytest.fixture
def tmp_kb_dir():
    """Temporary directory with KB subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        events_path = tmpdir / "events"
        events_path.mkdir()

        research_path = tmpdir / "research"
        research_path.mkdir()
        (research_path / "actors").mkdir()

        yield {
            "tmpdir": tmpdir,
            "events_path": events_path,
            "research_path": research_path,
            "db_path": tmpdir / "index.db",
        }


@pytest.fixture
def kb_configs(tmp_kb_dir):
    """KBConfig objects for events and research KBs."""
    events_kb = KBConfig(
        name="test-events",
        path=tmp_kb_dir["events_path"],
        kb_type=KBType.EVENTS,
        description="Test events KB",
    )
    research_kb = KBConfig(
        name="test-research",
        path=tmp_kb_dir["research_path"],
        kb_type=KBType.RESEARCH,
        description="Test research KB",
    )
    return {"events_kb": events_kb, "research_kb": research_kb}


@pytest.fixture
def pyrite_config(tmp_kb_dir, kb_configs):
    """PyriteConfig with events and research KBs."""
    return PyriteConfig(
        knowledge_bases=[kb_configs["events_kb"], kb_configs["research_kb"]],
        settings=Settings(index_path=tmp_kb_dir["db_path"]),
    )


@pytest.fixture
def pyrite_db(pyrite_config):
    """PyriteDB instance. Closed automatically after test."""
    db = PyriteDB(pyrite_config.settings.index_path)
    yield db
    db.close()


@pytest.fixture
def index_mgr(pyrite_db, pyrite_config):
    """IndexManager instance."""
    return IndexManager(pyrite_db, pyrite_config)


@pytest.fixture
def kb_service(pyrite_config, pyrite_db):
    """KBService instance."""
    return KBService(pyrite_config, pyrite_db)


@pytest.fixture
def sample_events(kb_configs):
    """Create 3 sample event entries on disk."""
    events_repo = KBRepository(kb_configs["events_kb"])
    entries = []
    for i in range(3):
        event = EventEntry.create(
            date=f"2025-01-{10 + i:02d}",
            title=f"Test Event {i}",
            body=f"Body for event {i} about immigration policy.",
            importance=5 + i,
        )
        event.tags = ["test", "immigration"]
        event.participants = ["Stephen Miller", "Tom Homan"]
        events_repo.save(event)
        entries.append(event)
    return entries


@pytest.fixture
def sample_person(kb_configs):
    """Create a sample person entry on disk."""
    research_repo = KBRepository(kb_configs["research_kb"])
    actor = PersonEntry.create(
        name="Stephen Miller", role="Immigration policy architect", importance=9
    )
    actor.body = "Stephen Miller biography."
    actor.tags = ["trump-admin", "immigration"]
    research_repo.save(actor)
    return actor


@pytest.fixture
def indexed_test_env(pyrite_config, pyrite_db, index_mgr, kb_configs, sample_events, sample_person):
    """Fully indexed test environment with sample data.

    Returns dict with config, db, index_mgr, events_kb, research_kb.
    """
    index_mgr.index_all()
    return {
        "config": pyrite_config,
        "db": pyrite_db,
        "index_mgr": index_mgr,
        "events_kb": kb_configs["events_kb"],
        "research_kb": kb_configs["research_kb"],
    }


@pytest.fixture
def rest_api_env(indexed_test_env):
    """Test environment for REST API tests with TestClient.

    Sets up FastAPI app globals and returns dict with client, config, db, kbs.
    """
    from starlette.testclient import TestClient

    import pyrite.server.api as api_module
    from pyrite.server.api import create_app

    config = indexed_test_env["config"]
    db = indexed_test_env["db"]
    index_mgr = indexed_test_env["index_mgr"]

    api_module._config = config
    api_module._db = db
    api_module._index_mgr = index_mgr
    api_module._kb_service = None  # Reset cached service

    app = create_app(config)
    client = TestClient(app)

    yield {
        "client": client,
        "config": config,
        "db": db,
        "events_kb": indexed_test_env["events_kb"],
        "research_kb": indexed_test_env["research_kb"],
    }

    api_module._config = None
    api_module._db = None
    api_module._index_mgr = None
    api_module._kb_service = None
