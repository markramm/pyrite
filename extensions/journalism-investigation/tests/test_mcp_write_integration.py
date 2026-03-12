"""Integration tests for write-tier MCP tool handlers.

These tests set up a real KBService + PyriteDB to verify
that write-tier tools create entries that read-tier tools can query.
"""

import pytest
from dataclasses import dataclass
from typing import Any

from pyrite.config import PyriteConfig, Settings, KBConfig
from pyrite.storage.database import PyriteDB
from pyrite.services.kb_service import KBService

from pyrite_journalism_investigation.plugin import JournalismInvestigationPlugin


@dataclass
class FakePluginContext:
    """Minimal context for injecting KBService into the plugin."""

    config: PyriteConfig
    db: PyriteDB
    kb_service: KBService
    kb_name: str = "test"
    user: str = "test-user"
    operation: str = "mcp"


@pytest.fixture
def setup(tmp_path):
    """Set up a temporary KB with KBService for integration testing."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    kb = KBConfig(name="test", path=kb_path, kb_type="journalism-investigation")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    kb_service = KBService(config, db)

    plugin = JournalismInvestigationPlugin()
    ctx = FakePluginContext(config=config, db=db, kb_service=kb_service)
    plugin.set_context(ctx)

    write_tools = plugin.get_mcp_tools("write")
    read_tools = plugin.get_mcp_tools("read")

    yield {
        "plugin": plugin,
        "db": db,
        "kb_service": kb_service,
        "write": write_tools,
        "read": read_tools,
    }
    db.close()


class TestCreateEntityRoundTrip:
    def test_create_asset_and_query_entities(self, setup):
        """Create an asset via write tool, query it via entities read tool."""
        create = setup["write"]["investigation_create_entity"]["handler"]
        query = setup["read"]["investigation_entities"]["handler"]

        result = create({
            "entity_type": "asset",
            "title": "London Belgravia Mansion",
            "body": "Five-storey townhouse in Belgravia.",
            "importance": 8,
            "fields": {"asset_type": "real_estate", "jurisdiction": "United Kingdom"},
            "tags": ["london", "luxury"],
            "kb_name": "test",
        })

        assert "error" not in result
        assert "created" in result
        assert result["type"] == "asset"

        entities = query({"kb_name": "test", "entity_type": "asset"})
        assert entities["count"] >= 1
        ids = [e["id"] for e in entities["entities"]]
        assert result["created"] in ids

    def test_create_person_and_query(self, setup):
        """Person resolves to 'actor' in DB — handler aliases should find it."""
        create = setup["write"]["investigation_create_entity"]["handler"]
        query = setup["read"]["investigation_entities"]["handler"]

        result = create({
            "entity_type": "person",
            "title": "Dmitry Oligarchov",
            "body": "Sanctioned individual.",
            "importance": 9,
            "kb_name": "test",
        })
        assert "error" not in result
        assert "created" in result

        entities = query({"kb_name": "test", "entity_type": "person"})
        assert entities["count"] >= 1
        ids = [e["id"] for e in entities["entities"]]
        assert result["created"] in ids

    def test_create_entity_invalid_type(self, setup):
        create = setup["write"]["investigation_create_entity"]["handler"]
        result = create({
            "entity_type": "spaceship",
            "title": "Test",
            "kb_name": "test",
        })
        assert "error" in result
        assert "spaceship" in result["error"]


class TestCreateEventRoundTrip:
    def test_create_event_and_query_timeline(self, setup):
        """Create an event via write tool, query it via timeline read tool."""
        create = setup["write"]["investigation_create_event"]["handler"]
        query = setup["read"]["investigation_timeline"]["handler"]

        result = create({
            "event_type": "investigation_event",
            "title": "Sanctions Announced",
            "date": "2022-02-24",
            "body": "EU sanctions package announced.",
            "importance": 9,
            "kb_name": "test",
        })

        assert "error" not in result
        assert "created" in result

        timeline = query({"kb_name": "test"})
        assert timeline["count"] >= 1
        ids = [e["id"] for e in timeline["events"]]
        assert result["created"] in ids

    def test_create_transaction_and_query(self, setup):
        create = setup["write"]["investigation_create_event"]["handler"]
        query = setup["read"]["investigation_timeline"]["handler"]

        result = create({
            "event_type": "transaction",
            "title": "Wire Transfer to Cyprus",
            "date": "2019-06-15",
            "fields": {"sender": "[[oligarchov]]", "receiver": "[[cyprus-corp]]", "amount": "5000000"},
            "kb_name": "test",
        })
        assert "error" not in result

        timeline = query({"kb_name": "test", "event_type": "transaction"})
        assert timeline["count"] >= 1

    def test_create_event_invalid_type(self, setup):
        create = setup["write"]["investigation_create_event"]["handler"]
        result = create({
            "event_type": "spaceship_launch",
            "title": "Test",
            "date": "2020-01-01",
            "kb_name": "test",
        })
        assert "error" in result


class TestCreateClaimRoundTrip:
    def test_create_claim_and_query(self, setup):
        """Create a claim, query it via claims read tool."""
        create = setup["write"]["investigation_create_claim"]["handler"]
        query = setup["read"]["investigation_claims"]["handler"]

        result = create({
            "title": "Oligarchov owns London mansion",
            "assertion": "Dmitry Oligarchov is the beneficial owner of the Belgravia mansion via Cyprus nominee.",
            "evidence_refs": ["[[panama-papers-doc-4427]]"],
            "importance": 8,
            "kb_name": "test",
        })

        assert "error" not in result
        assert "created" in result
        assert result["type"] == "claim"

        claims = query({"kb_name": "test"})
        assert claims["count"] >= 1
        ids = [c["id"] for c in claims["claims"]]
        assert result["created"] in ids

    def test_create_claim_no_evidence_warns(self, setup):
        """Claims with no evidence should succeed but warn."""
        create = setup["write"]["investigation_create_claim"]["handler"]
        result = create({
            "title": "Unsubstantiated claim",
            "assertion": "Something happened.",
            "kb_name": "test",
        })
        assert "error" not in result
        assert "warnings" in result
        assert any("evidence" in w.lower() for w in result["warnings"])


class TestLogSourceRoundTrip:
    def test_log_source_and_query(self, setup):
        """Log a source document, query it via sources read tool."""
        create = setup["write"]["investigation_log_source"]["handler"]
        query = setup["read"]["investigation_sources"]["handler"]

        result = create({
            "title": "Panama Papers Document 4427",
            "reliability": "high",
            "classification": "leaked",
            "obtained_method": "ICIJ database",
            "body": "Mossack Fonseca incorporation document.",
            "importance": 9,
            "kb_name": "test",
        })

        assert "error" not in result
        assert "created" in result
        assert result["type"] == "document_source"

        sources = query({"kb_name": "test"})
        assert sources["count"] >= 1
        ids = [s["id"] for s in sources["sources"]]
        assert result["created"] in ids

    def test_log_source_filter_by_reliability(self, setup):
        """Sources can be filtered by reliability level."""
        create = setup["write"]["investigation_log_source"]["handler"]

        create({
            "title": "High Reliability Source",
            "reliability": "high",
            "kb_name": "test",
        })
        create({
            "title": "Low Reliability Source",
            "reliability": "low",
            "kb_name": "test",
        })

        query = setup["read"]["investigation_sources"]["handler"]
        high_sources = query({"kb_name": "test", "reliability": "high"})
        low_sources = query({"kb_name": "test", "reliability": "low"})

        assert high_sources["count"] >= 1
        assert low_sources["count"] >= 1
        # They should be different sets
        high_ids = {s["id"] for s in high_sources["sources"]}
        low_ids = {s["id"] for s in low_sources["sources"]}
        assert not high_ids.intersection(low_ids)


class TestEvidenceChainRoundTrip:
    def test_full_evidence_chain(self, setup):
        """Create source → claim with evidence ref → trace chain."""
        log_source = setup["write"]["investigation_log_source"]["handler"]
        create_claim = setup["write"]["investigation_create_claim"]["handler"]
        trace = setup["read"]["investigation_evidence_chain"]["handler"]

        # Create a source document
        source_result = log_source({
            "title": "Bank Statement March 2019",
            "reliability": "high",
            "classification": "leaked",
            "kb_name": "test",
        })
        assert "error" not in source_result

        # Create a claim referencing evidence (evidence entry doesn't exist yet — gap expected)
        claim_result = create_claim({
            "title": "Transfer occurred in March 2019",
            "assertion": "A $5M transfer from Account A to Account B occurred.",
            "evidence_refs": ["[[evidence-bank-statement]]"],
            "kb_name": "test",
        })
        assert "error" not in claim_result

        # Trace the chain — should report gap for missing evidence entry
        chain = trace({"claim_id": claim_result["created"], "kb_name": "test"})
        assert "error" not in chain
        assert chain["claim"]["id"] == claim_result["created"]
        assert len(chain["gaps"]) >= 1  # evidence entry doesn't exist
