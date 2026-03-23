"""Tests for QA review REST endpoints."""

import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db
from pyrite.storage.database import PyriteDB


@pytest.fixture
def setup(tmp_path):
    """Create app, client, and seed a KB entry on disk + in DB."""
    kb_path = tmp_path / "kb"
    kb_path.mkdir()

    # Write a real markdown file so the service can read content
    entry_file = kb_path / "entry-1.md"
    entry_file.write_text("---\ntitle: Test Entry\ntype: note\n---\nHello world\n")

    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="generic")],
        settings=Settings(index_path=tmp_path / "index.db"),
    )

    app = create_app(config=config)
    db = PyriteDB(tmp_path / "index.db")
    app.dependency_overrides[get_config] = lambda: config
    app.dependency_overrides[get_db] = lambda: db

    # Index the entry so it exists in the DB
    db.register_kb("test-kb", "generic", str(kb_path))
    db.upsert_entry(
        {
            "id": "entry-1",
            "kb_name": "test-kb",
            "entry_type": "note",
            "title": "Test Entry",
            "body": "Hello world",
            "file_path": str(entry_file),
        }
    )

    client = TestClient(app)
    return client, db, kb_path


class TestCreateReview:
    def test_create_review(self, setup):
        client, db, _ = setup
        resp = client.post(
            "/api/reviews",
            json={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
                "reviewer": "alice",
                "reviewer_type": "user",
                "result": "pass",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["entry_id"] == "entry-1"
        assert data["result"] == "pass"
        assert len(data["content_hash"]) == 40

    def test_create_review_with_details(self, setup):
        client, db, _ = setup
        resp = client.post(
            "/api/reviews",
            json={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
                "reviewer": "bot",
                "reviewer_type": "agent",
                "result": "partial",
                "details": '{"clarity": "pass", "accuracy": "fail"}',
            },
        )
        assert resp.status_code == 200
        assert resp.json()["details"] == '{"clarity": "pass", "accuracy": "fail"}'

    def test_create_review_invalid_result(self, setup):
        client, _, _ = setup
        resp = client.post(
            "/api/reviews",
            json={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
                "reviewer": "alice",
                "reviewer_type": "user",
                "result": "invalid",
            },
        )
        assert resp.status_code == 422

    def test_create_review_invalid_reviewer_type(self, setup):
        client, _, _ = setup
        resp = client.post(
            "/api/reviews",
            json={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
                "reviewer": "alice",
                "reviewer_type": "robot",
                "result": "pass",
            },
        )
        assert resp.status_code == 422

    def test_create_review_nonexistent_entry(self, setup):
        client, _, _ = setup
        resp = client.post(
            "/api/reviews",
            json={
                "entry_id": "no-such-entry",
                "kb_name": "test-kb",
                "reviewer": "alice",
                "reviewer_type": "user",
                "result": "pass",
            },
        )
        assert resp.status_code == 404


class TestListReviews:
    def test_list_empty(self, setup):
        client, _, _ = setup
        resp = client.get("/api/reviews", params={"entry_id": "entry-1", "kb_name": "test-kb"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_list_after_create(self, setup):
        client, _, _ = setup
        client.post(
            "/api/reviews",
            json={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
                "reviewer": "alice",
                "reviewer_type": "user",
                "result": "pass",
            },
        )
        resp = client.get("/api/reviews", params={"entry_id": "entry-1", "kb_name": "test-kb"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 1


class TestLatestReview:
    def test_latest_none(self, setup):
        client, _, _ = setup
        resp = client.get(
            "/api/reviews/latest",
            params={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
            },
        )
        assert resp.status_code == 404

    def test_latest_after_create(self, setup):
        client, _, _ = setup
        client.post(
            "/api/reviews",
            json={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
                "reviewer": "r1",
                "reviewer_type": "user",
                "result": "fail",
            },
        )
        client.post(
            "/api/reviews",
            json={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
                "reviewer": "r2",
                "reviewer_type": "agent",
                "result": "pass",
            },
        )
        resp = client.get(
            "/api/reviews/latest",
            params={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["reviewer"] == "r2"


class TestReviewStatus:
    def test_status_no_review(self, setup):
        client, _, _ = setup
        resp = client.get(
            "/api/reviews/status",
            params={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current"] is False
        assert data["review"] is None

    def test_status_current(self, setup):
        client, _, _ = setup
        client.post(
            "/api/reviews",
            json={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
                "reviewer": "alice",
                "reviewer_type": "user",
                "result": "pass",
            },
        )
        resp = client.get(
            "/api/reviews/status",
            params={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["current"] is True

    def test_status_stale_after_edit(self, setup):
        client, _, kb_path = setup
        client.post(
            "/api/reviews",
            json={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
                "reviewer": "alice",
                "reviewer_type": "user",
                "result": "pass",
            },
        )
        # Modify the file
        (kb_path / "entry-1.md").write_text("---\ntitle: Changed\ntype: note\n---\nNew body\n")

        resp = client.get(
            "/api/reviews/status",
            params={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["current"] is False


class TestDeleteReview:
    def test_delete_existing(self, setup):
        client, _, _ = setup
        create_resp = client.post(
            "/api/reviews",
            json={
                "entry_id": "entry-1",
                "kb_name": "test-kb",
                "reviewer": "alice",
                "reviewer_type": "user",
                "result": "pass",
            },
        )
        review_id = create_resp.json()["id"]
        resp = client.delete(f"/api/reviews/{review_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_nonexistent(self, setup):
        client, _, _ = setup
        resp = client.delete("/api/reviews/9999")
        assert resp.status_code == 404
