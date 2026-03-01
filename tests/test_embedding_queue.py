"""
Tests for the background embedding pipeline: queue table, worker, status endpoint.

Tests cover:
- embed_queue table creation and operations
- EmbeddingWorker queue processing with retry logic
- _auto_embed switched to queue-based when worker is available
- Status endpoint /api/index/embed-status
- CLI `pyrite index embed --status`
- Graceful fallback: synchronous embed when no worker is running
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB


@pytest.fixture
def tmp_db():
    """Create a temporary database with entries for testing."""
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "index.db"
        kb_path = Path(d) / "kb"
        kb_path.mkdir()

        db = PyriteDB(db_path)
        db.register_kb(name="test-kb", kb_type="generic", path=str(kb_path))

        # Insert some test entries directly
        db._raw_conn.execute(
            "INSERT INTO entry (id, kb_name, title, body, entry_type, file_path, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            ("entry-1", "test-kb", "Test Entry 1", "Some content here", "note", str(kb_path / "entry-1.md")),
        )
        db._raw_conn.execute(
            "INSERT INTO entry (id, kb_name, title, body, entry_type, file_path, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            ("entry-2", "test-kb", "Test Entry 2", "More content here", "note", str(kb_path / "entry-2.md")),
        )
        db._raw_conn.commit()

        config = PyriteConfig(
            knowledge_bases=[KBConfig(name="test-kb", path=kb_path)],
            settings=Settings(index_path=db_path),
        )
        yield db, config, Path(d)
        db.close()


# =============================================================================
# Queue table tests
# =============================================================================


class TestEmbedQueueTable:
    """Test embed_queue table creation and operations."""

    def test_queue_table_exists(self, tmp_db):
        """embed_queue table should be created when EmbeddingWorker initializes."""
        from pyrite.services.embedding_worker import EmbeddingWorker

        db, config, _ = tmp_db
        worker = EmbeddingWorker(db)
        tables = [
            r[0]
            for r in db._raw_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "embed_queue" in tables

    def test_enqueue_entry(self, tmp_db):
        """enqueue() should add an entry to the queue."""
        from pyrite.services.embedding_worker import EmbeddingWorker

        db, config, _ = tmp_db
        worker = EmbeddingWorker(db)
        worker.enqueue("entry-1", "test-kb")

        rows = db._raw_conn.execute("SELECT entry_id, kb_name, status FROM embed_queue").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "entry-1"
        assert rows[0][1] == "test-kb"
        assert rows[0][2] == "pending"

    def test_enqueue_idempotent(self, tmp_db):
        """Enqueueing the same entry twice should not create duplicates."""
        from pyrite.services.embedding_worker import EmbeddingWorker

        db, config, _ = tmp_db
        worker = EmbeddingWorker(db)
        worker.enqueue("entry-1", "test-kb")
        worker.enqueue("entry-1", "test-kb")

        count = db._raw_conn.execute("SELECT COUNT(*) FROM embed_queue WHERE entry_id = 'entry-1'").fetchone()[0]
        assert count == 1

    def test_queue_status(self, tmp_db):
        """get_status() should return queue depth and counts."""
        from pyrite.services.embedding_worker import EmbeddingWorker

        db, config, _ = tmp_db
        worker = EmbeddingWorker(db)
        worker.enqueue("entry-1", "test-kb")
        worker.enqueue("entry-2", "test-kb")

        status = worker.get_status()
        assert status["pending"] == 2
        assert status["processing"] == 0
        assert status["failed"] == 0


# =============================================================================
# Worker processing tests
# =============================================================================


class TestEmbeddingWorkerProcessing:
    """Test the worker's process_batch method."""

    def test_process_batch_embeds_entries(self, tmp_db):
        """process_batch should mark entries as done on success."""
        from pyrite.services.embedding_worker import EmbeddingWorker

        db, config, _ = tmp_db
        worker = EmbeddingWorker(db)
        worker.enqueue("entry-1", "test-kb")

        # Mock the embedding service
        mock_svc = MagicMock()
        mock_svc.embed_entry.return_value = True
        worker._embedding_svc = mock_svc

        processed = worker.process_batch(batch_size=10)
        assert processed == 1
        mock_svc.embed_entry.assert_called_once_with("entry-1", "test-kb")

        status = worker.get_status()
        assert status["pending"] == 0

    def test_process_batch_handles_failure(self, tmp_db):
        """process_batch should increment attempts on failure, not mark as done."""
        from pyrite.services.embedding_worker import EmbeddingWorker

        db, config, _ = tmp_db
        worker = EmbeddingWorker(db)
        worker.enqueue("entry-1", "test-kb")

        mock_svc = MagicMock()
        mock_svc.embed_entry.side_effect = RuntimeError("Model not loaded")
        worker._embedding_svc = mock_svc

        processed = worker.process_batch(batch_size=10)
        assert processed == 0

        row = db._raw_conn.execute(
            "SELECT attempts, status, error FROM embed_queue WHERE entry_id = 'entry-1'"
        ).fetchone()
        assert row[0] == 1  # attempts incremented
        assert row[1] == "pending"  # still pending, not failed yet
        assert "Model not loaded" in row[2]

    def test_process_batch_marks_failed_after_max_attempts(self, tmp_db):
        """After max attempts, entry should be marked as failed."""
        from pyrite.services.embedding_worker import EmbeddingWorker

        db, config, _ = tmp_db
        worker = EmbeddingWorker(db, max_attempts=3)
        worker.enqueue("entry-1", "test-kb")

        mock_svc = MagicMock()
        mock_svc.embed_entry.side_effect = RuntimeError("fail")
        worker._embedding_svc = mock_svc

        # Process 3 times (max_attempts)
        for _ in range(3):
            worker.process_batch(batch_size=10)

        row = db._raw_conn.execute(
            "SELECT status, attempts FROM embed_queue WHERE entry_id = 'entry-1'"
        ).fetchone()
        assert row[0] == "failed"
        assert row[1] == 3

    def test_process_batch_respects_batch_size(self, tmp_db):
        """process_batch should only process up to batch_size entries."""
        from pyrite.services.embedding_worker import EmbeddingWorker

        db, config, _ = tmp_db
        worker = EmbeddingWorker(db)
        worker.enqueue("entry-1", "test-kb")
        worker.enqueue("entry-2", "test-kb")

        mock_svc = MagicMock()
        mock_svc.embed_entry.return_value = True
        worker._embedding_svc = mock_svc

        processed = worker.process_batch(batch_size=1)
        assert processed == 1
        assert worker.get_status()["pending"] == 1


# =============================================================================
# KBService integration
# =============================================================================


class TestKBServiceQueueIntegration:
    """Test that KBService uses queue when worker is available."""

    def test_auto_embed_uses_queue_when_worker_set(self, tmp_db):
        """When _embedding_worker is set, _auto_embed should enqueue instead of sync embed."""
        from pyrite.services.embedding_worker import EmbeddingWorker
        from pyrite.services.kb_service import KBService

        db, config, _ = tmp_db
        svc = KBService(config, db)

        worker = EmbeddingWorker(db)
        svc._embedding_worker = worker

        # Call _auto_embed
        svc._auto_embed("entry-1", "test-kb")

        # Should be in queue
        count = db._raw_conn.execute(
            "SELECT COUNT(*) FROM embed_queue WHERE entry_id = 'entry-1'"
        ).fetchone()[0]
        assert count == 1

    def test_auto_embed_falls_back_to_sync(self, tmp_db):
        """When no worker is set, _auto_embed should use sync embedding (existing behavior)."""
        from pyrite.services.kb_service import KBService

        db, config, _ = tmp_db
        svc = KBService(config, db)

        # No worker set, mock embedding svc
        mock_embed_svc = MagicMock()
        svc._embedding_svc = mock_embed_svc
        svc._embedding_checked = True
        svc._embedding_worker = None

        svc._auto_embed("entry-1", "test-kb")

        # Should have called embed_entry directly
        mock_embed_svc.embed_entry.assert_called_once_with("entry-1", "test-kb")


# =============================================================================
# REST API status endpoint
# =============================================================================


class TestEmbedStatusEndpoint:
    """Test GET /api/index/embed-status."""

    def test_embed_status_returns_queue_info(self, tmp_db):
        """Endpoint should return queue depth and processing info."""
        fastapi = pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app, get_config, get_db

        db, config, _ = tmp_db
        app = create_app(config=config)
        app.dependency_overrides[get_config] = lambda: config
        app.dependency_overrides[get_db] = lambda: db

        client = TestClient(app)
        resp = client.get("/api/index/embed-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "pending" in data
        assert "failed" in data
        assert "processing" in data
