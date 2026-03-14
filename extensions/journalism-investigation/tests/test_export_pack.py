"""Tests for investigation pack export."""

import json

import pytest
from pyrite_journalism_investigation.export import (
    build_investigation_pack,
    export_as_json,
    export_as_markdown,
)

from pyrite.storage.database import PyriteDB


@pytest.fixture
def populated_db(tmp_path):
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    db = PyriteDB(tmp_path / "index.db")
    db.register_kb("test", "journalism-investigation", str(kb_path))

    # Entities
    db.upsert_entry({"id": "person-1", "kb_name": "test", "title": "John Doe", "entry_type": "person", "importance": 8})
    db.upsert_entry({"id": "org-1", "kb_name": "test", "title": "Shell Corp", "entry_type": "organization", "importance": 7})
    db.upsert_entry({"id": "asset-1", "kb_name": "test", "title": "Yacht Aurora", "entry_type": "asset", "importance": 5})
    db.upsert_entry({"id": "account-1", "kb_name": "test", "title": "Swiss Account", "entry_type": "account", "importance": 4})

    # Events (timeline)
    db.upsert_entry({
        "id": "event-1", "kb_name": "test", "title": "Meeting", "entry_type": "investigation_event",
        "date": "2024-01-15", "importance": 6,
        "metadata": {"actors": ["John Doe"], "verification_status": "verified"},
    })
    db.upsert_entry({
        "id": "txn-1", "kb_name": "test", "title": "Payment", "entry_type": "transaction",
        "date": "2024-02-01", "importance": 9,
        "metadata": {"sender": "[[person-1]]", "receiver": "[[org-1]]", "amount": "50000", "currency": "USD"},
    })
    db.upsert_entry({
        "id": "legal-1", "kb_name": "test", "title": "Lawsuit Filed", "entry_type": "legal_action",
        "date": "2024-03-10", "importance": 7,
        "metadata": {"parties": ["John Doe", "Shell Corp"], "case_type": "civil"},
    })

    # Connections
    db.upsert_entry({
        "id": "own-1", "kb_name": "test", "title": "Doe owns Shell Corp", "entry_type": "ownership",
        "importance": 8,
        "metadata": {"owner": "[[person-1]]", "asset": "[[org-1]]", "percentage": "100"},
    })
    db.upsert_entry({
        "id": "fund-1", "kb_name": "test", "title": "Shell Corp funding", "entry_type": "funding",
        "importance": 6,
        "metadata": {"funder": "[[org-1]]", "recipient": "[[account-1]]"},
    })

    # Claim + evidence + source
    db.upsert_entry({
        "id": "claim-1", "kb_name": "test", "title": "Corruption claim", "entry_type": "claim",
        "importance": 8,
        "metadata": {"assertion": "Doe bribed officials", "claim_status": "partially_verified", "confidence": "medium", "evidence_refs": ["[[evidence-1]]"]},
    })
    db.upsert_entry({
        "id": "evidence-1", "kb_name": "test", "title": "Bank records", "entry_type": "evidence",
        "importance": 7,
        "metadata": {"evidence_type": "document", "source_document": "[[source-1]]", "reliability": "high"},
    })
    db.upsert_entry({
        "id": "source-1", "kb_name": "test", "title": "FOIA Response #123", "entry_type": "document_source",
        "importance": 6,
        "metadata": {"reliability": "high", "classification": "foia", "url": "https://example.com/foia/123"},
    })

    yield db
    db.close()


@pytest.fixture
def empty_db(tmp_path):
    kb_path = tmp_path / "empty-kb"
    kb_path.mkdir()
    db = PyriteDB(tmp_path / "index.db")
    db.register_kb("empty", "journalism-investigation", str(kb_path))
    yield db
    db.close()


class TestBuildInvestigationPack:
    def test_pack_has_all_sections(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        assert "summary" in pack
        assert "timeline" in pack
        assert "entities" in pack
        assert "connections" in pack
        assert "claims" in pack
        assert "sources" in pack
        assert "evidence_chains" in pack

    def test_summary_includes_counts(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        summary = pack["summary"]
        assert summary["kb_name"] == "test"
        assert summary["counts"]["person"] == 1
        assert summary["counts"]["organization"] == 1
        assert summary["counts"]["claim"] == 1
        assert summary["counts"]["document_source"] == 1
        assert summary["counts"]["investigation_event"] == 1
        assert summary["counts"]["transaction"] == 1

    def test_timeline_sorted_by_date(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        timeline = pack["timeline"]
        assert len(timeline) == 3
        dates = [e["date"] for e in timeline]
        assert dates == sorted(dates)
        # First should be event-1 (2024-01-15), last legal-1 (2024-03-10)
        assert timeline[0]["id"] == "event-1"
        assert timeline[-1]["id"] == "legal-1"

    def test_entities_grouped_by_type(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        entities = pack["entities"]
        assert "person" in entities
        assert "organization" in entities
        assert "asset" in entities
        assert "account" in entities
        assert len(entities["person"]) == 1
        assert entities["person"][0]["title"] == "John Doe"

    def test_claims_include_evidence_count(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        claims = pack["claims"]
        assert len(claims) == 1
        assert claims[0]["evidence_count"] == 1

    def test_source_redaction(self, populated_db):
        pack = build_investigation_pack(populated_db, "test", redact_sources=True)
        sources = pack["sources"]
        assert len(sources) == 1
        assert sources[0]["title"] == "[REDACTED]"
        assert sources[0]["url"] == "[REDACTED]"

    def test_source_no_redaction(self, populated_db):
        pack = build_investigation_pack(populated_db, "test", redact_sources=False)
        sources = pack["sources"]
        assert sources[0]["title"] == "FOIA Response #123"
        assert sources[0]["url"] == "https://example.com/foia/123"

    def test_min_importance_filter(self, populated_db):
        pack = build_investigation_pack(populated_db, "test", min_importance=8)
        # Only entries with importance >= 8 should appear
        # person-1 (8), txn-1 (9), own-1 (8), claim-1 (8)
        timeline = pack["timeline"]
        assert all(e["importance"] >= 8 for e in timeline)
        # event-1 has importance 6, should be filtered
        assert not any(e["id"] == "event-1" for e in timeline)
        # txn-1 has importance 9, should remain
        assert any(e["id"] == "txn-1" for e in timeline)

    def test_connections_included(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        connections = pack["connections"]
        assert len(connections) == 2
        types = {c["type"] for c in connections}
        assert "ownership" in types
        assert "funding" in types

    def test_evidence_chains_for_claims(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        chains = pack["evidence_chains"]
        assert len(chains) == 1
        chain = chains[0]
        assert chain["claim"]["id"] == "claim-1"
        assert len(chain["evidence_chain"]) == 1
        assert chain["evidence_chain"][0]["evidence_id"] == "evidence-1"
        assert chain["evidence_chain"][0]["source_document"]["id"] == "source-1"


class TestEmptyKB:
    def test_empty_kb_produces_valid_pack(self, empty_db):
        pack = build_investigation_pack(empty_db, "empty")
        assert pack["summary"]["kb_name"] == "empty"
        assert pack["timeline"] == []
        assert pack["claims"] == []
        assert pack["sources"] == []
        assert pack["connections"] == []
        assert pack["evidence_chains"] == []
        # All entity groups should be empty
        for group in pack["entities"].values():
            assert group == []


class TestExportAsJson:
    def test_valid_json_output(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        result = export_as_json(pack)
        parsed = json.loads(result)
        assert parsed["summary"]["kb_name"] == "test"
        assert len(parsed["timeline"]) == 3

    def test_json_roundtrip(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        result = export_as_json(pack)
        parsed = json.loads(result)
        assert parsed == pack


class TestExportAsMarkdown:
    def test_has_section_headers(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        md = export_as_markdown(pack)
        assert "# Investigation Pack: test" in md
        assert "## Summary" in md
        assert "## Timeline" in md
        assert "## Entities" in md
        assert "## Claims" in md
        assert "## Sources" in md

    def test_timeline_table(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        md = export_as_markdown(pack)
        # Should have table header row
        assert "| Date" in md
        assert "2024-01-15" in md
        assert "Meeting" in md

    def test_claims_table(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        md = export_as_markdown(pack)
        assert "Corruption claim" in md
        assert "partially_verified" in md

    def test_redacted_sources_in_markdown(self, populated_db):
        pack = build_investigation_pack(populated_db, "test", redact_sources=True)
        md = export_as_markdown(pack)
        assert "[REDACTED]" in md
        assert "FOIA Response #123" not in md

    def test_entities_grouped(self, populated_db):
        pack = build_investigation_pack(populated_db, "test")
        md = export_as_markdown(pack)
        assert "### person" in md or "### Person" in md
        assert "John Doe" in md

    def test_empty_kb_markdown(self, empty_db):
        pack = build_investigation_pack(empty_db, "empty")
        md = export_as_markdown(pack)
        assert "# Investigation Pack: empty" in md
        assert "## Summary" in md
