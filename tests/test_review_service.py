"""Tests for ReviewService (extracted from KBService)."""

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.exceptions import EntryNotFoundError, KBNotFoundError
from pyrite.services.review_service import ReviewService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def review_setup(tmp_path):
    """Set up ReviewService with a KB containing an entry file."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()

    # Write an entry file
    entry_file = kb_path / "entry-1.md"
    entry_file.write_text("---\nid: entry-1\ntitle: Test Entry\ntype: note\n---\n\nHello world")

    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path)],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")

    # Index the entry so it's in the DB
    from pyrite.storage.index import IndexManager

    idx = IndexManager(db, config)
    idx.index_all()

    svc = ReviewService(config, db)
    yield svc, db
    db.close()


class TestReviewService:
    def test_create_review(self, review_setup):
        svc, db = review_setup
        review = svc.create_review(
            entry_id="entry-1",
            kb_name="test-kb",
            reviewer="tester",
            reviewer_type="user",
            result="pass",
        )
        assert review["entry_id"] == "entry-1"
        assert review["reviewer"] == "tester"
        assert review["result"] == "pass"
        assert review["content_hash"]

    def test_create_review_kb_not_found(self, review_setup):
        svc, db = review_setup
        with pytest.raises(KBNotFoundError):
            svc.create_review("entry-1", "nonexistent", "r", "user", "pass")

    def test_create_review_entry_not_found(self, review_setup):
        svc, db = review_setup
        with pytest.raises(EntryNotFoundError):
            svc.create_review("no-such-entry", "test-kb", "r", "user", "pass")

    def test_get_reviews(self, review_setup):
        svc, db = review_setup
        svc.create_review("entry-1", "test-kb", "r1", "user", "pass")
        svc.create_review("entry-1", "test-kb", "r2", "agent", "fail")
        reviews = svc.get_reviews("entry-1", "test-kb")
        assert len(reviews) == 2

    def test_get_latest_review(self, review_setup):
        svc, db = review_setup
        svc.create_review("entry-1", "test-kb", "r1", "user", "pass")
        svc.create_review("entry-1", "test-kb", "r2", "agent", "fail")
        latest = svc.get_latest_review("entry-1", "test-kb")
        assert latest is not None
        assert latest["reviewer"] == "r2"

    def test_is_review_current_unchanged(self, review_setup):
        svc, db = review_setup
        svc.create_review("entry-1", "test-kb", "r1", "user", "pass")
        status = svc.is_review_current("entry-1", "test-kb")
        assert status["current"] is True

    def test_is_review_current_after_edit(self, review_setup, tmp_path):
        svc, db = review_setup
        svc.create_review("entry-1", "test-kb", "r1", "user", "pass")

        # Modify the file
        entry_file = tmp_path / "test-kb" / "entry-1.md"
        entry_file.write_text("---\nid: entry-1\ntitle: Test Entry\ntype: note\n---\n\nChanged!")

        status = svc.is_review_current("entry-1", "test-kb")
        assert status["current"] is False

    def test_is_review_current_no_reviews(self, review_setup):
        svc, db = review_setup
        status = svc.is_review_current("entry-1", "test-kb")
        assert status["current"] is False
        assert status["review"] is None
