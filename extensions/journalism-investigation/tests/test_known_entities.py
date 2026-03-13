"""Tests for known-entities KB pattern and matching utility."""

import pytest

from pyrite.config import PyriteConfig, Settings, KBConfig
from pyrite.storage.database import PyriteDB
from pyrite.services.kb_service import KBService

from pyrite_journalism_investigation.plugin import JournalismInvestigationPlugin
from pyrite_journalism_investigation.known_entities import find_matching_entities


@pytest.fixture
def setup(tmp_path):
    """Set up temporary KBs for known-entities testing."""
    kb_path = tmp_path / "known-ents"
    kb_path.mkdir()
    kb = KBConfig(name="known-ents", path=kb_path, kb_type="known-entities")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    svc = KBService(config, db)

    yield {"db": db, "svc": svc}
    db.close()


class TestPresetRegistered:
    def test_preset_registered(self):
        plugin = JournalismInvestigationPlugin()
        presets = plugin.get_kb_presets()
        assert "known-entities" in presets
        preset = presets["known-entities"]
        assert "known entities" in preset["description"].lower()
        assert preset["kb_type"] == "known-entities"


class TestKBTypeRegistered:
    def test_kb_type_registered(self):
        plugin = JournalismInvestigationPlugin()
        kb_types = plugin.get_kb_types()
        assert "known-entities" in kb_types


class TestFindMatchingByTitle:
    def test_find_matching_by_title(self, setup):
        svc = setup["svc"]
        svc.create_entry("known-ents", "john-doe", "John Doe", "person")

        matches = find_matching_entities(setup["db"], "John Doe", ["known-ents"])
        assert len(matches) == 1
        assert matches[0]["id"] == "john-doe"
        assert matches[0]["kb_name"] == "known-ents"
        assert matches[0]["title"] == "John Doe"
        assert matches[0]["entry_type"] in ("person", "actor")
        assert matches[0]["match_type"] == "title"

    def test_find_matching_by_title_case_insensitive(self, setup):
        svc = setup["svc"]
        svc.create_entry("known-ents", "john-doe", "John Doe", "person")

        matches = find_matching_entities(setup["db"], "john doe", ["known-ents"])
        assert len(matches) == 1
        assert matches[0]["match_type"] == "title"


class TestFindMatchingByAlias:
    def test_find_matching_by_alias(self, setup):
        svc = setup["svc"]
        svc.create_entry(
            "known-ents", "acme-corp", "Acme Corporation", "organization",
            aliases=["Acme Corp", "ACME"],
        )

        matches = find_matching_entities(setup["db"], "Acme Corp", ["known-ents"])
        assert len(matches) == 1
        assert matches[0]["id"] == "acme-corp"
        assert matches[0]["match_type"] == "alias"

    def test_find_matching_by_alias_case_insensitive(self, setup):
        svc = setup["svc"]
        svc.create_entry(
            "known-ents", "acme-corp", "Acme Corporation", "organization",
            aliases=["Acme Corp", "ACME"],
        )

        matches = find_matching_entities(setup["db"], "acme", ["known-ents"])
        assert len(matches) == 1
        assert matches[0]["match_type"] == "alias"


class TestNoMatchReturnsEmpty:
    def test_no_match_returns_empty(self, setup):
        svc = setup["svc"]
        svc.create_entry("known-ents", "john-doe", "John Doe", "person")

        matches = find_matching_entities(setup["db"], "Jane Smith", ["known-ents"])
        assert matches == []

    def test_empty_kb_returns_empty(self, setup):
        matches = find_matching_entities(setup["db"], "anything", ["known-ents"])
        assert matches == []
