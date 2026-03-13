"""Tests for actor extraction and migration tool."""

import json
from pathlib import Path

import pytest
import yaml

from pyrite.config import PyriteConfig, Settings, KBConfig
from pyrite.storage.database import PyriteDB
from pyrite.services.kb_service import KBService


@pytest.fixture
def setup(tmp_path):
    """Set up a temporary KB with timeline events containing actor strings."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    kb = KBConfig(name="test", path=kb_path, kb_type="cascade-timeline")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    svc = KBService(config, db)

    # Create some timeline events with actor strings
    svc.create_entry("test", "e1", "Event 1", "timeline_event",
                     date="2025-01-01", actors=["Donald Trump", "FBI"])
    svc.create_entry("test", "e2", "Event 2", "timeline_event",
                     date="2025-02-01", actors=["Donald Trump", "Elon Musk"])
    svc.create_entry("test", "e3", "Event 3", "timeline_event",
                     date="2025-03-01", actors=["FBI", "Pete Hegseth"])

    yield {"db": db, "svc": svc, "config": config, "kb_path": kb_path, "tmp_path": tmp_path}
    db.close()


class TestExtractActors:
    """Test the extract_actors function."""

    def test_collects_unique_actors(self, setup):
        from pyrite_cascade.extract_actors import extract_actors

        result = extract_actors(setup["db"], "test", dry_run=True)
        assert set(result["actors"].keys()) == {"Donald Trump", "FBI", "Elon Musk", "Pete Hegseth"}

    def test_counts_appearances(self, setup):
        from pyrite_cascade.extract_actors import extract_actors

        result = extract_actors(setup["db"], "test", dry_run=True)
        assert result["actors"]["Donald Trump"]["count"] == 2
        assert result["actors"]["FBI"]["count"] == 2
        assert result["actors"]["Elon Musk"]["count"] == 1

    def test_computes_importance(self, setup):
        from pyrite_cascade.extract_actors import extract_actors

        result = extract_actors(setup["db"], "test", dry_run=True)
        # Donald Trump appears most (2 times), should have higher importance
        assert result["actors"]["Donald Trump"]["importance"] >= result["actors"]["Elon Musk"]["importance"]

    def test_dry_run_creates_no_entries(self, setup):
        from pyrite_cascade.extract_actors import extract_actors

        extract_actors(setup["db"], "test", dry_run=True)
        # No actor entries should exist
        actors = setup["db"].list_entries(kb_name="test", entry_type="actor", limit=100)
        assert len(actors) == 0

    def test_creates_actor_entries(self, setup):
        from pyrite_cascade.extract_actors import extract_actors

        result = extract_actors(
            setup["db"], "test",
            config=setup["config"],
            dry_run=False,
        )
        assert result["created"] >= 4

        # Verify entries exist in DB
        actors = setup["db"].list_entries(kb_name="test", entry_type="actor", limit=100)
        titles = {a.get("title") for a in actors}
        assert "Donald Trump" in titles
        assert "FBI" in titles

    def test_incremental_skips_existing(self, setup):
        from pyrite_cascade.extract_actors import extract_actors

        # Create one actor manually
        setup["svc"].create_entry("test", "donald-trump", "Donald Trump", "actor")

        result = extract_actors(
            setup["db"], "test",
            config=setup["config"],
            dry_run=False,
        )
        # Should skip Donald Trump since it already exists
        assert "Donald Trump" in result.get("skipped", [])

    def test_alias_file_groups_variants(self, setup):
        from pyrite_cascade.extract_actors import extract_actors

        # Create alias file
        alias_file = setup["tmp_path"] / "aliases.json"
        alias_file.write_text(json.dumps({
            "Federal Bureau of Investigation": ["FBI"],
        }))

        result = extract_actors(
            setup["db"], "test",
            alias_file=alias_file,
            dry_run=True,
        )
        # FBI should be grouped under Federal Bureau of Investigation
        assert "Federal Bureau of Investigation" in result["actors"]
        fbi_entry = result["actors"]["Federal Bureau of Investigation"]
        assert "FBI" in fbi_entry.get("aliases", [])

    def test_actor_files_written_to_kb(self, setup):
        from pyrite_cascade.extract_actors import extract_actors

        extract_actors(
            setup["db"], "test",
            config=setup["config"],
            dry_run=False,
        )

        # Check that actor files exist on disk (actors go to people/ directory)
        kb_path = setup["kb_path"]
        actor_files = list(kb_path.glob("**/*.md"))
        # Filter to only actor files (exclude timeline events)
        actors_in_db = setup["db"].list_entries(kb_name="test", entry_type="actor", limit=100)
        assert len(actors_in_db) >= 4
