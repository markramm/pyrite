"""Tests for unified cross-KB search with result correlation."""

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB

from pyrite_journalism_investigation.cross_kb_search import (
    cross_kb_search,
    correlate_results,
)


@pytest.fixture
def multi_kb_db(tmp_path):
    """DB with 3 KBs containing overlapping entities."""
    db = PyriteDB(tmp_path / "index.db")

    # Register 3 KBs
    kb1_path = tmp_path / "investigation-a"
    kb1_path.mkdir()
    kb2_path = tmp_path / "investigation-b"
    kb2_path.mkdir()
    kb3_path = tmp_path / "known-entities"
    kb3_path.mkdir()

    db.register_kb("investigation-a", "journalism-investigation", str(kb1_path))
    db.register_kb("investigation-b", "journalism-investigation", str(kb2_path))
    db.register_kb("known-entities", "known-entities", str(kb3_path))

    # KB A: investigation into ACME Corp
    db.upsert_entry({
        "id": "john-smith",
        "kb_name": "investigation-a",
        "title": "John Smith",
        "entry_type": "person",
        "body": "CEO of ACME Corp, suspected of fraud",
        "importance": 8,
        "tags": ["ceo", "suspect"],
    })
    db.upsert_entry({
        "id": "acme-corp",
        "kb_name": "investigation-a",
        "title": "ACME Corporation",
        "entry_type": "organization",
        "body": "Target company under investigation for financial fraud",
        "importance": 9,
        "tags": ["company", "target"],
    })
    db.upsert_entry({
        "id": "event-wire",
        "kb_name": "investigation-a",
        "title": "Suspicious wire transfer from ACME",
        "entry_type": "transaction",
        "body": "Wire transfer to offshore account",
        "date": "2025-06-15",
        "importance": 7,
    })

    # KB B: separate investigation also involving John Smith
    db.upsert_entry({
        "id": "john-smith-b",
        "kb_name": "investigation-b",
        "title": "John Smith",
        "entry_type": "person",
        "body": "Board member of BigCo, linked to lobbying",
        "importance": 6,
        "tags": ["board-member"],
    })
    db.upsert_entry({
        "id": "bigco-inc",
        "kb_name": "investigation-b",
        "title": "BigCo Inc",
        "entry_type": "organization",
        "body": "Government contractor under investigation",
        "importance": 7,
    })

    # Known entities KB: reference entry for John Smith
    db.upsert_entry({
        "id": "known-john-smith",
        "kb_name": "known-entities",
        "title": "John Smith",
        "entry_type": "person",
        "body": "Known entity: CEO of ACME Corp and board member of BigCo",
        "importance": 5,
        "metadata": {"aliases": ["J. Smith", "John Q. Smith"]},
    })

    yield db
    db.close()


class TestCrossKBSearch:
    """Test cross-KB search returning grouped results."""

    def test_search_returns_results_from_multiple_kbs(self, multi_kb_db):
        result = cross_kb_search(multi_kb_db, "John Smith")
        # Should find results in at least 2 KBs
        kb_names = {r["kb_name"] for group in result["groups"] for r in group["results"]}
        assert len(kb_names) >= 2

    def test_results_grouped_by_kb(self, multi_kb_db):
        result = cross_kb_search(multi_kb_db, "John Smith")
        assert "groups" in result
        for group in result["groups"]:
            assert "kb_name" in group
            assert "results" in group
            assert "count" in group
            # All results in a group should be from the same KB
            for r in group["results"]:
                assert r["kb_name"] == group["kb_name"]

    def test_total_count(self, multi_kb_db):
        result = cross_kb_search(multi_kb_db, "John Smith")
        total = sum(g["count"] for g in result["groups"])
        assert result["total_count"] == total

    def test_query_preserved(self, multi_kb_db):
        result = cross_kb_search(multi_kb_db, "ACME")
        assert result["query"] == "ACME"

    def test_no_results_returns_empty(self, multi_kb_db):
        result = cross_kb_search(multi_kb_db, "xyznonexistent")
        assert result["total_count"] == 0
        assert result["groups"] == []

    def test_limit_applies(self, multi_kb_db):
        result = cross_kb_search(multi_kb_db, "John Smith", limit=1)
        assert result["total_count"] <= 1

    def test_kb_filter(self, multi_kb_db):
        result = cross_kb_search(
            multi_kb_db, "John Smith",
            kb_names=["investigation-a"],
        )
        kb_names = {g["kb_name"] for g in result["groups"]}
        assert kb_names == {"investigation-a"}

    def test_results_include_snippet(self, multi_kb_db):
        result = cross_kb_search(multi_kb_db, "ACME")
        for group in result["groups"]:
            for r in group["results"]:
                # snippet may or may not be present depending on FTS match
                assert "id" in r
                assert "title" in r


class TestCorrelateResults:
    """Test entity correlation across KBs."""

    def test_correlates_by_title(self, multi_kb_db):
        # Flat results with same title across KBs
        flat_results = [
            {"id": "john-smith", "kb_name": "investigation-a", "title": "John Smith",
             "entry_type": "person", "importance": 8},
            {"id": "john-smith-b", "kb_name": "investigation-b", "title": "John Smith",
             "entry_type": "person", "importance": 6},
            {"id": "known-john-smith", "kb_name": "known-entities", "title": "John Smith",
             "entry_type": "person", "importance": 5},
        ]
        correlated = correlate_results(flat_results)
        assert len(correlated) >= 1
        # The "John Smith" group should contain entries from multiple KBs
        john_group = [g for g in correlated if g["title"] == "John Smith"]
        assert len(john_group) == 1
        assert john_group[0]["kb_count"] >= 2

    def test_different_entities_not_correlated(self, multi_kb_db):
        flat_results = [
            {"id": "john-smith", "kb_name": "investigation-a", "title": "John Smith",
             "entry_type": "person", "importance": 8},
            {"id": "acme-corp", "kb_name": "investigation-a", "title": "ACME Corporation",
             "entry_type": "organization", "importance": 9},
        ]
        correlated = correlate_results(flat_results)
        assert len(correlated) == 2

    def test_correlation_includes_kb_appearances(self, multi_kb_db):
        flat_results = [
            {"id": "john-smith", "kb_name": "investigation-a", "title": "John Smith",
             "entry_type": "person", "importance": 8},
            {"id": "john-smith-b", "kb_name": "investigation-b", "title": "John Smith",
             "entry_type": "person", "importance": 6},
        ]
        correlated = correlate_results(flat_results)
        john_group = correlated[0]
        assert "appearances" in john_group
        kb_names = {a["kb_name"] for a in john_group["appearances"]}
        assert "investigation-a" in kb_names
        assert "investigation-b" in kb_names

    def test_correlated_sorted_by_kb_count(self, multi_kb_db):
        flat_results = [
            {"id": "john-smith", "kb_name": "investigation-a", "title": "John Smith",
             "entry_type": "person", "importance": 8},
            {"id": "john-smith-b", "kb_name": "investigation-b", "title": "John Smith",
             "entry_type": "person", "importance": 6},
            {"id": "acme-corp", "kb_name": "investigation-a", "title": "ACME Corporation",
             "entry_type": "organization", "importance": 9},
        ]
        correlated = correlate_results(flat_results)
        # John Smith (2 KBs) should rank before ACME Corp (1 KB)
        assert correlated[0]["title"] == "John Smith"
        assert correlated[0]["kb_count"] == 2

    def test_empty_input(self, multi_kb_db):
        correlated = correlate_results([])
        assert correlated == []
