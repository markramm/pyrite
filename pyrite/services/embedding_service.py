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


def _embedding_to_blob(embedding: list[float]) -> bytes:
    """Serialize float32 list to bytes for sqlite-vec."""
    return struct.pack(f"{len(embedding)}f", *embedding)


def _blob_to_embedding(blob: bytes) -> list[float]:
    """Deserialize bytes to float32 list from sqlite-vec."""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def _generate_snippet(entry: dict[str, Any], max_len: int = 200, query: str = "") -> str:
    """Generate a text snippet from an entry for search results.

    When a query is provided, finds the paragraph with the most keyword
    overlap to explain why the entry matched (relevance-aware snippeting).
    """
    body = entry.get("body") or ""

    # If we have a query, find the most relevant passage
    if query and body:
        best = _best_passage(body, query, max_len)
        if best:
            return best

    # Prefer summary if available
    if entry.get("summary"):
        text = entry["summary"]
        return text[:max_len] + "..." if len(text) > max_len else text
    # Fall back to body
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


def _best_passage(body: str, query: str, max_len: int = 200) -> str:
    """Find the paragraph in body most relevant to the query.

    Uses keyword overlap scoring (fast, no embedding needed).
    Returns the best-matching passage or empty string.
    """
    import re

    # Tokenize query into lowercase words
    query_terms = set(re.findall(r"\w{3,}", query.lower()))
    if not query_terms:
        return ""

    # Split body into paragraphs
    # Strip markdown headers, emphasis, etc.
    clean = re.sub(r"^#{1,6}\s*", "", body, flags=re.MULTILINE)
    clean = re.sub(r"\*\*(.+?)\*\*", r"\1", clean)
    clean = re.sub(r"\*(.+?)\*", r"\1", clean)
    paragraphs = [p.strip() for p in clean.split("\n\n") if p.strip() and len(p.strip()) > 20]

    if not paragraphs:
        return ""

    # Score each paragraph by keyword overlap
    best_score = 0
    best_para = ""
    for para in paragraphs:
        para_terms = set(re.findall(r"\w{3,}", para.lower()))
        overlap = len(query_terms & para_terms)
        # Bonus for query term density
        score = overlap + (overlap / max(len(para_terms), 1)) * 0.5
        if score > best_score:
            best_score = score
            best_para = para

    if best_score == 0:
        return ""

    # Trim to max length
    if len(best_para) > max_len:
        return best_para[:max_len] + "..."
    return best_para


class EmbeddingService:
    """
    Service for generating and querying vector embeddings.

    Uses sentence-transformers for local embedding generation and
    the SearchBackend for vector storage and KNN search.
    """

    def __init__(self, db: PyriteDB, model_name: str = "all-MiniLM-L6-v2"):
        self.db = db
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            import logging

            # Suppress noisy output during model loading:
            # - transformers.disable_progress_bar() silences weight-loading tqdm bars
            # - Log levels silence the HF load report and auth warnings
            import transformers.utils.logging as tf_logging
            from sentence_transformers import SentenceTransformer

            tf_logging.disable_progress_bar()
            loggers = ["transformers", "huggingface_hub"]
            old_levels = {name: logging.getLogger(name).level for name in loggers}
            for name in loggers:
                logging.getLogger(name).setLevel(logging.ERROR)
            try:
                self._model = SentenceTransformer(self.model_name)
            finally:
                for name, level in old_levels.items():
                    logging.getLogger(name).setLevel(level)
                tf_logging.enable_progress_bar()
        return self._model

    def prewarm(self) -> bool:
        """Pre-load the embedding model to avoid cold-start latency.

        Returns True if model was loaded successfully, False if dependencies
        are missing or loading failed.
        """
        if not is_available():
            return False
        try:
            self._get_model()
            logger.info("Embedding model '%s' pre-warmed", self.model_name)
            return True
        except Exception:
            logger.warning("Failed to pre-warm embedding model", exc_info=True)
            return False

    @property
    def is_warm(self) -> bool:
        """Whether the embedding model is already loaded."""
        return self._model is not None

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a text string."""
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_entry(self, entry_id: str, kb_name: str) -> bool:
        """Embed a single entry and store via backend. Returns True on success."""
        backend = self.db.backend
        if not backend.vec_available:
            return False

        entry = self.db.get_entry(entry_id, kb_name)
        if not entry:
            return False

        text = _entry_text(entry)
        if not text.strip():
            return False

        embedding = self.embed_text(text)
        return backend.upsert_embedding(entry_id, kb_name, embedding)

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
        backend = self.db.backend
        if not backend.vec_available:
            return {"embedded": 0, "skipped": 0, "errors": 0}

        stats = {"embedded": 0, "skipped": 0, "errors": 0}

        rows = backend.get_entries_for_embedding(kb_name)
        total = len(rows)

        # Get already-embedded rowids (unless force)
        embedded_rowids = set()
        if not force:
            embedded_rowids = backend.get_embedded_rowids()

        for i, row in enumerate(rows):
            if progress_callback:
                progress_callback(i, total)

            rowid = row.get("rowid")
            if not force and rowid in embedded_rowids:
                stats["skipped"] += 1
                continue

            try:
                text = _entry_text(row)
                if not text.strip():
                    stats["skipped"] += 1
                    continue

                embedding = self.embed_text(text)
                backend.upsert_embedding(row["id"], row["kb_name"], embedding)
                stats["embedded"] += 1
            except Exception as e:
                logger.warning("Failed to embed entry %s: %s", row.get("id"), e)
                stats["errors"] += 1

        if progress_callback:
            progress_callback(total, total)

        return stats

    def search_similar(
        self,
        query: str,
        kb_name: str | None = None,
        limit: int = 20,
        max_distance: float = 1.3,
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
        backend = self.db.backend
        if not backend.vec_available:
            return []

        embedding = self.embed_text(query)
        results = backend.search_semantic(
            embedding=embedding,
            kb_name=kb_name,
            limit=limit,
            max_distance=max_distance,
        )

        # Add relevance-aware snippets to results
        for entry in results:
            if not entry.get("snippet"):
                entry["snippet"] = _generate_snippet(entry, query=query)

        return results

    def has_embeddings(self) -> bool:
        """Check if any embeddings exist in the database."""
        return self.db.backend.has_embeddings()

    def embedding_stats(self) -> dict[str, Any]:
        """Get embedding statistics."""
        return self.db.backend.embedding_stats()
