"""Tests for EvidenceEntry type."""

from pyrite_journalism_investigation.entry_types import EvidenceEntry, EVIDENCE_TYPES


class TestEvidenceEntry:
    def test_entry_type(self):
        entry = EvidenceEntry(id="e1", title="Bank record")
        assert entry.entry_type == "evidence"

    def test_round_trip(self):
        entry = EvidenceEntry(
            id="e1",
            title="Wire transfer record",
            body="Shows $500k transfer on 2020-03-15",
            evidence_type="record",
            source_document="[[doc-bank-leak]]",
            reliability="high",
            obtained_date="2021-06-01",
            chain_of_custody="Obtained via FOIA request #12345",
            importance=8,
        )
        meta = entry.to_frontmatter()
        assert meta["type"] == "evidence"
        assert meta["evidence_type"] == "record"
        assert meta["source_document"] == "[[doc-bank-leak]]"
        assert meta["reliability"] == "high"
        assert meta["obtained_date"] == "2021-06-01"
        assert meta["chain_of_custody"] == "Obtained via FOIA request #12345"

        restored = EvidenceEntry.from_frontmatter(meta, "Shows $500k transfer on 2020-03-15")
        assert restored.id == "e1"
        assert restored.evidence_type == "record"
        assert restored.source_document == "[[doc-bank-leak]]"
        assert restored.reliability == "high"
        assert restored.obtained_date == "2021-06-01"
        assert restored.chain_of_custody == "Obtained via FOIA request #12345"
        assert restored.importance == 8

    def test_defaults(self):
        entry = EvidenceEntry(id="e1", title="Test")
        assert entry.evidence_type == ""
        assert entry.source_document == ""
        assert entry.reliability == "unknown"
        assert entry.obtained_date == ""
        assert entry.chain_of_custody == ""
        assert entry.importance == 5

    def test_to_frontmatter_omits_empty(self):
        entry = EvidenceEntry(id="e1", title="Test")
        meta = entry.to_frontmatter()
        assert "evidence_type" not in meta
        assert "source_document" not in meta
        assert "obtained_date" not in meta
        assert "chain_of_custody" not in meta

    def test_evidence_type_values(self):
        assert "document" in EVIDENCE_TYPES
        assert "testimony" in EVIDENCE_TYPES
        assert "record" in EVIDENCE_TYPES
        assert "data" in EVIDENCE_TYPES
        assert "photo" in EVIDENCE_TYPES
        assert "video" in EVIDENCE_TYPES
        assert "other" in EVIDENCE_TYPES
