"""
Background Embedding Worker

Manages a SQLite-backed queue of entries to embed asynchronously.
Decouples write latency from embedding computation.

Usage:
    worker = EmbeddingWorker(db)
    worker.enqueue("entry-id", "kb-name")
    processed = worker.process_batch(batch_size=10)
    status = worker.get_status()
"""

import logging
from datetime import UTC, datetime

from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


class EmbeddingWorker:
    """Background embedding worker with SQLite-backed queue."""

    def __init__(self, db: PyriteDB, max_attempts: int = 3):
        self.db = db
        self.max_attempts = max_attempts
        self._embedding_svc = None
        self._ensure_table()

    def _ensure_table(self):
        """Create the embed_queue table if it doesn't exist."""
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS embed_queue (
                entry_id TEXT NOT NULL,
                kb_name TEXT NOT NULL,
                queued_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                error TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (entry_id, kb_name)
            )
        """)
        self.db.conn.commit()

    def enqueue(self, entry_id: str, kb_name: str) -> None:
        """Add an entry to the embedding queue. Idempotent — skips if already queued."""
        now = datetime.now(UTC).isoformat()
        self.db.conn.execute(
            """
            INSERT OR IGNORE INTO embed_queue (entry_id, kb_name, queued_at, status, attempts)
            VALUES (?, ?, ?, 'pending', 0)
            """,
            (entry_id, kb_name, now),
        )
        self.db.conn.commit()

    def process_batch(self, batch_size: int = 10) -> int:
        """Process up to batch_size pending entries. Returns count of successfully embedded."""
        rows = self.db.conn.execute(
            """
            SELECT entry_id, kb_name, attempts FROM embed_queue
            WHERE status = 'pending' AND attempts < ?
            ORDER BY queued_at ASC
            LIMIT ?
            """,
            (self.max_attempts, batch_size),
        ).fetchall()

        if not rows:
            return 0

        svc = self._get_embedding_svc()
        if svc is None:
            logger.debug("Embedding service not available, skipping batch")
            return 0

        success_count = 0
        for row in rows:
            entry_id, kb_name, attempts = row[0], row[1], row[2]
            try:
                svc.embed_entry(entry_id, kb_name)
                # Mark as done — delete from queue
                self.db.conn.execute(
                    "DELETE FROM embed_queue WHERE entry_id = ? AND kb_name = ?",
                    (entry_id, kb_name),
                )
                success_count += 1
            except Exception as e:
                new_attempts = attempts + 1
                new_status = "failed" if new_attempts >= self.max_attempts else "pending"
                self.db.conn.execute(
                    """
                    UPDATE embed_queue
                    SET attempts = ?, status = ?, error = ?
                    WHERE entry_id = ? AND kb_name = ?
                    """,
                    (new_attempts, new_status, str(e), entry_id, kb_name),
                )
                logger.warning(
                    "Embed failed for %s (attempt %d/%d): %s",
                    entry_id, new_attempts, self.max_attempts, e,
                )

        self.db.conn.commit()
        return success_count

    def get_status(self) -> dict:
        """Get queue status: counts by status."""
        rows = self.db.conn.execute(
            "SELECT status, COUNT(*) FROM embed_queue GROUP BY status"
        ).fetchall()
        counts = {r[0]: r[1] for r in rows}
        return {
            "pending": counts.get("pending", 0),
            "processing": counts.get("processing", 0),
            "failed": counts.get("failed", 0),
            "total": sum(counts.values()),
        }

    def _get_embedding_svc(self):
        """Get or lazy-load embedding service."""
        if self._embedding_svc is not None:
            return self._embedding_svc
        try:
            from .embedding_service import EmbeddingService, is_available

            if is_available() and self.db.vec_available:
                self._embedding_svc = EmbeddingService(self.db)
                return self._embedding_svc
        except Exception:
            logger.warning("Embedding service initialization failed in worker", exc_info=True)
        return None
