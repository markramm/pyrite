"""
Background Index Worker

Manages background index sync/rebuild jobs using a SQLite-backed job table
and threads. Follows the same pattern as EmbeddingWorker but tracks
per-KB bulk operations rather than per-entry queue items.

Usage:
    worker = IndexWorker(db, config)
    job_id = worker.submit_sync(kb_name="my-kb")
    status = worker.get_job(job_id)
"""

import logging
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from ..config import PyriteConfig
from ..storage.database import PyriteDB
from ..storage.index import IndexManager

logger = logging.getLogger(__name__)


class IndexWorker:
    """Background index worker with SQLite-backed job tracking."""

    def __init__(self, db: PyriteDB, config: PyriteConfig):
        self.db = db
        self.config = config
        self._lock = threading.Lock()
        # Optional progress callback: on_progress(job_id, current, total).
        # Called from worker THREADS, not the main thread — callers must
        # handle cross-thread concerns (e.g. asyncio bridge).
        self.on_progress: Callable[[str, int, int], None] | None = None
        self._ensure_table()

    def _ensure_table(self):
        """Create the index_job table if it doesn't exist."""
        self.db._raw_conn.execute("""
            CREATE TABLE IF NOT EXISTS index_job (
                job_id TEXT PRIMARY KEY,
                kb_name TEXT,
                operation TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                progress_current INTEGER DEFAULT 0,
                progress_total INTEGER DEFAULT 0,
                added INTEGER DEFAULT 0,
                updated INTEGER DEFAULT 0,
                removed INTEGER DEFAULT 0,
                error TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        self.db._raw_conn.commit()

    def submit_sync(self, kb_name: str | None = None) -> str:
        """Submit a background sync job. Returns job_id.

        If an active sync job already exists for the same kb_name, returns
        its job_id instead of creating a duplicate.
        """
        with self._lock:
            # Check for existing active job
            existing = self._find_active_job("sync", kb_name)
            if existing:
                return existing

            job_id = uuid.uuid4().hex[:12]
            now = datetime.now(UTC).isoformat()
            self.db._raw_conn.execute(
                """
                INSERT INTO index_job (job_id, kb_name, operation, status, created_at)
                VALUES (?, ?, 'sync', 'pending', ?)
                """,
                (job_id, kb_name, now),
            )
            self.db._raw_conn.commit()

        thread = threading.Thread(
            target=self._run_sync, args=(job_id, kb_name), daemon=True
        )
        thread.start()
        return job_id

    def submit_rebuild(self, kb_name: str) -> str:
        """Submit a background rebuild job. Returns job_id."""
        with self._lock:
            existing = self._find_active_job("rebuild", kb_name)
            if existing:
                return existing

            job_id = uuid.uuid4().hex[:12]
            now = datetime.now(UTC).isoformat()
            self.db._raw_conn.execute(
                """
                INSERT INTO index_job (job_id, kb_name, operation, status, created_at)
                VALUES (?, ?, 'rebuild', 'pending', ?)
                """,
                (job_id, kb_name, now),
            )
            self.db._raw_conn.commit()

        thread = threading.Thread(
            target=self._run_rebuild, args=(job_id, kb_name), daemon=True
        )
        thread.start()
        return job_id

    def get_job(self, job_id: str) -> dict | None:
        """Get job status by ID."""
        row = self.db._raw_conn.execute(
            "SELECT * FROM index_job WHERE job_id = ?", (job_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def get_active_jobs(self) -> list[dict]:
        """Get all pending/running jobs."""
        rows = self.db._raw_conn.execute(
            "SELECT * FROM index_job WHERE status IN ('pending', 'running') ORDER BY created_at"
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_recent_jobs(self, limit: int = 20) -> list[dict]:
        """Get recent jobs (all statuses), ordered by creation time descending."""
        rows = self.db._raw_conn.execute(
            "SELECT * FROM index_job ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def _find_active_job(self, operation: str, kb_name: str | None) -> str | None:
        """Find an existing active job for the same operation/kb. Returns job_id or None."""
        if kb_name:
            row = self.db._raw_conn.execute(
                """
                SELECT job_id FROM index_job
                WHERE operation = ? AND kb_name = ? AND status IN ('pending', 'running')
                """,
                (operation, kb_name),
            ).fetchone()
        else:
            row = self.db._raw_conn.execute(
                """
                SELECT job_id FROM index_job
                WHERE operation = ? AND kb_name IS NULL AND status IN ('pending', 'running')
                """,
                (operation,),
            ).fetchone()
        return row[0] if row else None

    def _run_sync(self, job_id: str, kb_name: str | None):
        """Thread target for sync jobs.

        Creates its own DB connection to avoid SQLite threading issues.
        """
        db = PyriteDB(self.db.db_path)
        index_mgr = IndexManager(db, self.config)
        try:
            self._update_status(db, job_id, "running")

            def progress_cb(current: int, total: int):
                self._update_progress(db, job_id, current, total)

            results = index_mgr.sync_incremental(kb_name, progress_callback=progress_cb)

            now = datetime.now(UTC).isoformat()
            db._raw_conn.execute(
                """
                UPDATE index_job
                SET status = 'completed', added = ?, updated = ?, removed = ?,
                    completed_at = ?
                WHERE job_id = ?
                """,
                (results["added"], results["updated"], results["removed"], now, job_id),
            )
            db._raw_conn.commit()
        except Exception as e:
            logger.error("Index sync job %s failed: %s", job_id, e, exc_info=True)
            now = datetime.now(UTC).isoformat()
            try:
                db._raw_conn.execute(
                    """
                    UPDATE index_job
                    SET status = 'failed', error = ?, completed_at = ?
                    WHERE job_id = ?
                    """,
                    (str(e), now, job_id),
                )
                db._raw_conn.commit()
            except Exception:
                logger.debug("Failed to update job status after error", exc_info=True)
        finally:
            db.close()

    def _run_rebuild(self, job_id: str, kb_name: str):
        """Thread target for rebuild jobs.

        Creates its own DB connection to avoid SQLite threading issues.
        """
        db = PyriteDB(self.db.db_path)
        index_mgr = IndexManager(db, self.config)
        try:
            self._update_status(db, job_id, "running")

            def progress_cb(current: int, total: int):
                self._update_progress(db, job_id, current, total)

            count = index_mgr.index_kb(kb_name, progress_cb)

            now = datetime.now(UTC).isoformat()
            db._raw_conn.execute(
                """
                UPDATE index_job
                SET status = 'completed', added = ?, completed_at = ?
                WHERE job_id = ?
                """,
                (count, now, job_id),
            )
            db._raw_conn.commit()
        except Exception as e:
            logger.error("Index rebuild job %s failed: %s", job_id, e, exc_info=True)
            now = datetime.now(UTC).isoformat()
            try:
                db._raw_conn.execute(
                    """
                    UPDATE index_job
                    SET status = 'failed', error = ?, completed_at = ?
                    WHERE job_id = ?
                    """,
                    (str(e), now, job_id),
                )
                db._raw_conn.commit()
            except Exception:
                logger.debug("Failed to update job status after error", exc_info=True)
        finally:
            db.close()

    @staticmethod
    def _update_status(db: PyriteDB, job_id: str, status: str):
        """Update job status using the given DB connection."""
        db._raw_conn.execute(
            "UPDATE index_job SET status = ? WHERE job_id = ?",
            (status, job_id),
        )
        db._raw_conn.commit()

    def _update_progress(self, db: PyriteDB, job_id: str, current: int, total: int):
        """Update progress columns and optionally call on_progress callback."""
        db._raw_conn.execute(
            "UPDATE index_job SET progress_current = ?, progress_total = ? WHERE job_id = ?",
            (current, total, job_id),
        )
        db._raw_conn.commit()
        if self.on_progress:
            try:
                self.on_progress(job_id, current, total)
            except Exception:
                logger.debug("on_progress callback failed", exc_info=True)

    @staticmethod
    def _row_to_dict(row) -> dict:
        """Convert a sqlite3.Row or tuple to a dict."""
        if hasattr(row, "keys"):
            return dict(row)
        # Fallback for tuple rows
        cols = [
            "job_id", "kb_name", "operation", "status",
            "progress_current", "progress_total",
            "added", "updated", "removed",
            "error", "created_at", "completed_at",
        ]
        return dict(zip(cols, row, strict=False))
