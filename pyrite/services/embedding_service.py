"""
Embedding Service for Semantic Search

Provides vector embeddings via sentence-transformers and sqlite-vec for
semantic similarity search across knowledge base entries.

Requires optional dependencies: pip install pyrite[semantic]
"""

import logging
import struct
from typing import Any

from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """Check if sentence-transformers is installed."""
    try:
        import sentence_transformers  # noqa: F401

        return True
    except ImportError:
        return False


def _entry_text(entry: dict[str, Any]) -> str:
    """Combine entry fields into text for embedding."""
    parts = []
    if entry.get("title"):
        parts.append(entry["title"])
    if entry.get("summary"):
        parts.append(entry["summary"])
    body = entry.get("body") or ""
    if body:
        parts.append(body[:500])
    return " ".join(parts)


def _generate_snippet(entry: dict[str, Any], max_len: int = 200) -> str:
    """Generate a text snippet from an entry for search results."""
    # Prefer summary if available
    if entry.get("summary"):
        text = entry["summary"]
        return text[:max_len] + "..." if len(text) > max_len else text
    # Fall back to body
    body = entry.get("body") or ""
    if not body:
        return ""
    # Strip markdown formatting for cleaner snippet
    text = body.strip()
    # Take first paragraph-ish chunk
    for sep in ["\n\n", "\n"]:
        idx = text.find(sep)
        if 0 < idx < max_len * 2:
            text = text[:idx]
            break
    return text[:max_len] + "..." if len(text) > max_len else text


def _embedding_to_blob(embedding: list[float]) -> bytes:
    """Serialize float32 list to bytes for sqlite-vec."""
    return struct.pack(f"{len(embedding)}f", *embedding)


def _blob_to_embedding(blob: bytes) -> list[float]:
    """Deserialize bytes to float32 list from sqlite-vec."""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


class EmbeddingService:
    """
    Service for generating and querying vector embeddings.

    Uses sentence-transformers for local embedding generation and
    sqlite-vec for vector storage and KNN search.
    """

    def __init__(self, db: PyriteDB, model_name: str = "all-MiniLM-L6-v2"):
        self.db = db
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a text string."""
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_entry(self, entry_id: str, kb_name: str) -> bool:
        """Embed a single entry and store in vec_entry. Returns True on success."""
        if not self.db.vec_available:
            return False

        entry = self.db.get_entry(entry_id, kb_name)
        if not entry:
            return False

        text = _entry_text(entry)
        if not text.strip():
            return False

        embedding = self.embed_text(text)
        blob = _embedding_to_blob(embedding)

        # Get the rowid for this entry
        row = self.db.conn.execute(
            "SELECT rowid FROM entry WHERE id = ? AND kb_name = ?",
            (entry_id, kb_name),
        ).fetchone()
        if not row:
            return False

        rowid = row[0]

        # Upsert into vec_entry
        self.db.conn.execute("DELETE FROM vec_entry WHERE rowid = ?", (rowid,))
        self.db.conn.execute(
            "INSERT INTO vec_entry(rowid, embedding) VALUES (?, ?)",
            (rowid, blob),
        )
        self.db.conn.commit()
        return True

    def embed_all(
        self,
        kb_name: str | None = None,
        force: bool = False,
        progress_callback: Any = None,
    ) -> dict[str, int]:
        """
        Batch embed all entries.

        Args:
            kb_name: Limit to specific KB (None for all)
            force: Re-embed even if already embedded
            progress_callback: Optional callable(current, total)

        Returns:
            Dict with embedded, skipped, errors counts
        """
        if not self.db.vec_available:
            return {"embedded": 0, "skipped": 0, "errors": 0}

        stats = {"embedded": 0, "skipped": 0, "errors": 0}

        # Get all entries
        if kb_name:
            rows = self.db.conn.execute(
                "SELECT rowid, id, kb_name, title, summary, body FROM entry WHERE kb_name = ?",
                (kb_name,),
            ).fetchall()
        else:
            rows = self.db.conn.execute(
                "SELECT rowid, id, kb_name, title, summary, body FROM entry"
            ).fetchall()

        total = len(rows)

        # Get already-embedded rowids (unless force)
        embedded_rowids = set()
        if not force:
            vec_rows = self.db.conn.execute("SELECT rowid FROM vec_entry").fetchall()
            embedded_rowids = {r[0] for r in vec_rows}

        for i, row in enumerate(rows):
            if progress_callback:
                progress_callback(i, total)

            rowid = row[0]

            if not force and rowid in embedded_rowids:
                stats["skipped"] += 1
                continue

            try:
                entry_dict = dict(row)
                text = _entry_text(entry_dict)
                if not text.strip():
                    stats["skipped"] += 1
                    continue

                embedding = self.embed_text(text)
                blob = _embedding_to_blob(embedding)

                self.db.conn.execute("DELETE FROM vec_entry WHERE rowid = ?", (rowid,))
                self.db.conn.execute(
                    "INSERT INTO vec_entry(rowid, embedding) VALUES (?, ?)",
                    (rowid, blob),
                )
                stats["embedded"] += 1
            except Exception as e:
                logger.warning("Failed to embed entry %s: %s", row[1], e)
                stats["errors"] += 1

        self.db.conn.commit()

        if progress_callback:
            progress_callback(total, total)

        return stats

    def search_similar(
        self,
        query: str,
        kb_name: str | None = None,
        limit: int = 20,
        max_distance: float = 1.1,
    ) -> list[dict[str, Any]]:
        """
        Search for semantically similar entries using vector KNN.

        Args:
            query: Natural language search query.
            kb_name: Optional KB filter.
            limit: Max results to return.
            max_distance: Cosine distance cutoff (0=identical, 2=opposite).
                Results with distance > max_distance are excluded.

        Returns list of entry dicts with 'distance' and 'snippet' fields.
        """
        if not self.db.vec_available:
            return []

        embedding = self.embed_text(query)
        blob = _embedding_to_blob(embedding)

        # Use sqlite-vec KNN query with k constraint
        # Fetch more than limit to allow for kb_name filtering + distance cutoff
        fetch_limit = limit * 3 if kb_name else limit * 2

        rows = self.db.conn.execute(
            """
            SELECT v.rowid, v.distance, e.*
            FROM vec_entry v
            JOIN entry e ON v.rowid = e.rowid
            WHERE v.embedding MATCH ? AND k = ?
            ORDER BY v.distance
            """,
            (blob, fetch_limit),
        ).fetchall()

        results = []
        for row in rows:
            entry = dict(row)
            # Apply relevance cutoff
            distance = entry.get("distance", 0)
            if distance > max_distance:
                continue
            if kb_name and entry.get("kb_name") != kb_name:
                continue
            # Generate snippet for semantic results
            if not entry.get("snippet"):
                entry["snippet"] = _generate_snippet(entry)
            results.append(entry)
            if len(results) >= limit:
                break

        return results

    def has_embeddings(self) -> bool:
        """Check if any embeddings exist in the database."""
        if not self.db.vec_available:
            return False
        row = self.db.conn.execute("SELECT COUNT(*) FROM vec_entry").fetchone()
        return row[0] > 0

    def embedding_stats(self) -> dict[str, Any]:
        """Get embedding statistics."""
        if not self.db.vec_available:
            return {"available": False, "count": 0, "total_entries": 0}

        vec_count = self.db.conn.execute("SELECT COUNT(*) FROM vec_entry").fetchone()[0]
        entry_count = self.db.conn.execute("SELECT COUNT(*) FROM entry").fetchone()[0]

        return {
            "available": True,
            "count": vec_count,
            "total_entries": entry_count,
            "coverage": f"{vec_count / entry_count * 100:.1f}%" if entry_count > 0 else "0%",
        }
