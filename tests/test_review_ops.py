"""Tests for ReviewOpsMixin DB operations."""

from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB


@pytest.fixture
def db(tmp_path):
    """Create a fresh PyriteDB with a test KB and entry."""
    database = PyriteDB(tmp_path / "test.db")
    database.register_kb("test-kb", "generic", str(tmp_path / "kb"))
    database.upsert_entry({
        "id": "entry-1",
        "kb_name": "test-kb",
        "entry_type": "note",
        "title": "Test Entry",
        "body": "Hello",
    })
    return database


class TestCreateReview:
    def test_create_returns_dict(self, db):
        review = db.create_review(
            entry_id="entry-1",
            kb_name="test-kb",
            content_hash="a" * 40,
            reviewer="alice",
            reviewer_type="user",
            result="pass",
        )
        assert review["entry_id"] == "entry-1"
        assert review["kb_name"] == "test-kb"
        assert review["content_hash"] == "a" * 40
        assert review["reviewer"] == "alice"
        assert review["reviewer_type"] == "user"
        assert review["result"] == "pass"
        assert review["id"] is not None
        assert review["created_at"] is not None

    def test_create_with_details(self, db):
        review = db.create_review(
            entry_id="entry-1",
            kb_name="test-kb",
            content_hash="b" * 40,
            reviewer="bot-1",
            reviewer_type="agent",
            result="partial",
            details='{"rubric_1": "pass", "rubric_2": "fail"}',
        )
        assert review["details"] == '{"rubric_1": "pass", "rubric_2": "fail"}'


class TestGetReviews:
    def test_empty(self, db):
        assert db.get_reviews("entry-1", "test-kb") == []

    def test_returns_newest_first(self, db):
        db.create_review("entry-1", "test-kb", "a" * 40, "r1", "user", "pass")
        db.create_review("entry-1", "test-kb", "b" * 40, "r2", "user", "fail")
        reviews = db.get_reviews("entry-1", "test-kb")
        assert len(reviews) == 2
        # Second created should be first (newest)
        assert reviews[0]["reviewer"] == "r2"
        assert reviews[1]["reviewer"] == "r1"

    def test_limit(self, db):
        for i in range(5):
            db.create_review("entry-1", "test-kb", f"{i:0>40}", f"r{i}", "user", "pass")
        assert len(db.get_reviews("entry-1", "test-kb", limit=3)) == 3


class TestGetLatestReview:
    def test_none_when_empty(self, db):
        assert db.get_latest_review("entry-1", "test-kb") is None

    def test_returns_most_recent(self, db):
        db.create_review("entry-1", "test-kb", "a" * 40, "r1", "user", "pass")
        db.create_review("entry-1", "test-kb", "b" * 40, "r2", "agent", "fail")
        latest = db.get_latest_review("entry-1", "test-kb")
        assert latest["reviewer"] == "r2"
        assert latest["result"] == "fail"


class TestDeleteReview:
    def test_delete_existing(self, db):
        review = db.create_review("entry-1", "test-kb", "a" * 40, "r1", "user", "pass")
        assert db.delete_review(review["id"]) is True
        assert db.get_reviews("entry-1", "test-kb") == []

    def test_delete_nonexistent(self, db):
        assert db.delete_review(999) is False


class TestCascadeOnEntryDelete:
    def test_reviews_deleted_with_entry(self, db):
        db.create_review("entry-1", "test-kb", "a" * 40, "r1", "user", "pass")
        db.create_review("entry-1", "test-kb", "b" * 40, "r2", "agent", "fail")
        assert len(db.get_reviews("entry-1", "test-kb")) == 2

        db.delete_entry("entry-1", "test-kb")
        assert db.get_reviews("entry-1", "test-kb") == []
