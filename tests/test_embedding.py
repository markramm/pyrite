"""Tests for embedding service and semantic search.

These tests require sentence-transformers and sqlite-vec.
The entire file is skipped if those dependencies are not installed.
"""

import tempfile
from pathlib import Path

# Skip entire module if sentence-transformers is not installed
import pytest

st = pytest.importorskip("sentence_transformers")


from pyrite.config import KBType  # noqa: E402
from pyrite.services.embedding_service import (  # noqa: E402
    EmbeddingService,
    _blob_to_embedding,
    _embedding_to_blob,
    _entry_text,
    is_available,
)
from pyrite.storage.database import PyriteDB  # noqa: E402


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def test_db(temp_dir):
    """Create test database with vec support."""
    db = PyriteDB(temp_dir / "test.db")
    assert db.vec_available, "sqlite-vec not loaded"
    yield db
    db.close()


@pytest.fixture
def populated_db(test_db):
    """Database with sample entries for testing."""
    test_db.register_kb("test-kb", KBType.RESEARCH, "/tmp/test")

    entries = [
        {
            "id": "climate-policy",
            "kb_name": "test-kb",
            "entry_type": "theme",
            "title": "Climate Policy and Environmental Regulations",
            "summary": "Overview of climate change policy and environmental protection measures",
            "body": "The climate crisis demands immediate policy action on carbon emissions.",
            "tags": [],
            "actors": [],
            "sources": [],
            "links": [],
        },
        {
            "id": "tax-reform",
            "kb_name": "test-kb",
            "entry_type": "theme",
            "title": "Tax Reform Proposals",
            "summary": "Analysis of proposed changes to the tax code",
            "body": "Tax reform proposals include changes to corporate and individual tax rates.",
            "tags": [],
            "actors": [],
            "sources": [],
            "links": [],
        },
        {
            "id": "immigration",
            "kb_name": "test-kb",
            "entry_type": "theme",
            "title": "Immigration and Border Security",
            "summary": "Immigration policy including border enforcement and visa programs",
            "body": "Immigration reform covers border security, visa processing, and asylum policies.",
            "tags": [],
            "actors": [],
            "sources": [],
            "links": [],
        },
    ]

    for entry in entries:
        test_db.upsert_entry(entry)

    return test_db


class TestAvailability:
    """Test dependency availability checks."""

    def test_is_available(self):
        """sentence-transformers is available (we importskipped above)."""
        assert is_available() is True


class TestBlobConversion:
    """Test float32 serialization roundtrip."""

    def test_roundtrip(self):
        """Embedding blob conversion is lossless."""
        original = [0.1, 0.2, -0.3, 0.0, 1.0, -1.0]
        blob = _embedding_to_blob(original)
        recovered = _blob_to_embedding(blob)

        assert len(recovered) == len(original)
        for a, b in zip(original, recovered, strict=False):
            assert abs(a - b) < 1e-6

    def test_blob_size(self):
        """384-dim embedding produces 1536-byte blob (384 * 4 bytes)."""
        embedding = [0.0] * 384
        blob = _embedding_to_blob(embedding)
        assert len(blob) == 384 * 4


class TestEntryText:
    """Test text extraction from entries."""

    def test_combines_fields(self):
        """_entry_text combines title, summary, and body."""
        entry = {
            "title": "Test Title",
            "summary": "Test summary",
            "body": "Test body content",
        }
        text = _entry_text(entry)
        assert "Test Title" in text
        assert "Test summary" in text
        assert "Test body content" in text

    def test_truncates_body(self):
        """Body is truncated to 500 chars."""
        entry = {
            "title": "Title",
            "summary": None,
            "body": "x" * 1000,
        }
        text = _entry_text(entry)
        # Title (5) + space (1) + body (500) = 506
        assert len(text) <= 506

    def test_handles_missing_fields(self):
        """Missing fields are skipped gracefully."""
        entry = {"title": "Only Title", "summary": None, "body": None}
        text = _entry_text(entry)
        assert text == "Only Title"

    def test_all_fields_empty(self):
        """All-empty entry produces empty string."""
        entry = {"title": None, "summary": None, "body": None}
        text = _entry_text(entry)
        assert text == ""

    def test_empty_dict(self):
        """Missing keys produce empty string."""
        text = _entry_text({})
        assert text == ""


class TestEmbeddingService:
    """Test EmbeddingService operations."""

    def test_embed_text_dimensions(self, test_db):
        """Embedding has 384 dimensions."""
        svc = EmbeddingService(test_db)
        embedding = svc.embed_text("test text")
        assert len(embedding) == 384

    def test_embed_single_entry(self, populated_db):
        """embed_entry stores embedding for a single entry."""
        svc = EmbeddingService(populated_db)

        result = svc.embed_entry("climate-policy", "test-kb")
        assert result is True

        # Verify it's stored
        count = populated_db._raw_conn.execute("SELECT COUNT(*) FROM vec_entry").fetchone()[0]
        assert count == 1

    def test_embed_entry_not_found(self, test_db):
        """embed_entry returns False for missing entry."""
        svc = EmbeddingService(test_db)
        result = svc.embed_entry("nonexistent", "test-kb")
        assert result is False

    def test_embed_all(self, populated_db):
        """embed_all embeds all entries."""
        svc = EmbeddingService(populated_db)

        stats = svc.embed_all()

        assert stats["embedded"] == 3
        assert stats["skipped"] == 0
        assert stats["errors"] == 0

    def test_embed_all_incremental(self, populated_db):
        """embed_all skips already-embedded entries."""
        svc = EmbeddingService(populated_db)

        # First pass
        stats1 = svc.embed_all()
        assert stats1["embedded"] == 3

        # Second pass (incremental)
        stats2 = svc.embed_all()
        assert stats2["embedded"] == 0
        assert stats2["skipped"] == 3

    def test_embed_all_force(self, populated_db):
        """embed_all with force re-embeds everything."""
        svc = EmbeddingService(populated_db)

        svc.embed_all()
        stats = svc.embed_all(force=True)

        assert stats["embedded"] == 3
        assert stats["skipped"] == 0

    def test_embed_all_by_kb(self, populated_db):
        """embed_all can filter by KB name."""
        svc = EmbeddingService(populated_db)

        stats = svc.embed_all(kb_name="test-kb")
        assert stats["embedded"] == 3

        stats = svc.embed_all(kb_name="nonexistent")
        assert stats["embedded"] == 0

    def test_has_embeddings(self, populated_db):
        """has_embeddings returns correct state."""
        svc = EmbeddingService(populated_db)

        assert svc.has_embeddings() is False

        svc.embed_all()

        assert svc.has_embeddings() is True

    def test_embedding_stats(self, populated_db):
        """embedding_stats returns count information."""
        svc = EmbeddingService(populated_db)
        svc.embed_all()

        stats = svc.embedding_stats()
        assert stats["available"] is True
        assert stats["count"] == 3
        assert stats["total_entries"] == 3


class TestSimilaritySearch:
    """Test vector similarity search."""

    def test_search_returns_results(self, populated_db):
        """search_similar returns relevant results."""
        svc = EmbeddingService(populated_db)
        svc.embed_all()

        results = svc.search_similar("environmental regulations")

        assert len(results) > 0
        # Climate policy should be most relevant to "environmental regulations"
        ids = [r["id"] for r in results]
        assert "climate-policy" in ids

    def test_search_ordering(self, populated_db):
        """Climate query should rank climate entry first."""
        svc = EmbeddingService(populated_db)
        svc.embed_all()

        results = svc.search_similar("climate change carbon emissions")

        assert len(results) > 0
        assert results[0]["id"] == "climate-policy"

    def test_search_with_kb_filter(self, populated_db):
        """search_similar filters by KB name."""
        svc = EmbeddingService(populated_db)
        svc.embed_all()

        results = svc.search_similar("policy", kb_name="test-kb")
        assert len(results) > 0

        results = svc.search_similar("policy", kb_name="nonexistent")
        assert len(results) == 0

    def test_search_limit(self, populated_db):
        """search_similar respects limit."""
        svc = EmbeddingService(populated_db)
        svc.embed_all()

        results = svc.search_similar("policy", limit=1)
        assert len(results) == 1

    def test_search_no_embeddings(self, populated_db):
        """search_similar returns empty when no embeddings exist."""
        svc = EmbeddingService(populated_db)
        results = svc.search_similar("anything")
        assert results == []
