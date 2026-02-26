"""Tests for PluginContext.search_semantic() method."""

import pytest
from unittest.mock import MagicMock, patch

from pyrite.plugins.context import PluginContext


class TestPluginSemanticSearch:
    """Tests for semantic search in plugin context."""

    def _make_ctx(self, **kwargs):
        """Create a PluginContext with mocked dependencies."""
        config = MagicMock()
        db = MagicMock()
        return PluginContext(config=config, db=db, **kwargs)

    def test_search_semantic_falls_back_to_fts(self):
        """When embeddings not available, falls back to FTS5."""
        ctx = self._make_ctx(kb_name="test-kb")
        ctx.db.vec_available = False

        mock_svc = MagicMock()
        mock_svc.search.return_value = [{"id": "test", "title": "Test"}]
        mock_search_cls = MagicMock(return_value=mock_svc)

        with patch.dict(
            "sys.modules",
            {
                "pyrite.services.search_service": MagicMock(
                    SearchService=mock_search_cls
                )
            },
        ):
            results = ctx.search_semantic("test query")
            assert len(results) == 1
            assert results[0]["id"] == "test"
            mock_search_cls.assert_called_once_with(ctx.db)
            mock_svc.search.assert_called_once_with(
                "test query", kb_name="test-kb", limit=10
            )

    def test_search_semantic_uses_kb_name_param(self):
        """kb_name parameter overrides context kb_name."""
        ctx = self._make_ctx(kb_name="default-kb")
        ctx.db.vec_available = False

        mock_svc = MagicMock()
        mock_svc.search.return_value = [{"id": "x", "title": "X"}]
        mock_search_cls = MagicMock(return_value=mock_svc)

        with patch.dict(
            "sys.modules",
            {
                "pyrite.services.search_service": MagicMock(
                    SearchService=mock_search_cls
                )
            },
        ):
            results = ctx.search_semantic("query", kb_name="other-kb")
            mock_svc.search.assert_called_once_with(
                "query", kb_name="other-kb", limit=10
            )

    def test_search_semantic_returns_empty_on_error(self):
        """Returns empty list when all search methods fail."""
        ctx = self._make_ctx()
        ctx.db.vec_available = False

        mock_search_cls = MagicMock(side_effect=Exception("DB error"))

        with patch.dict(
            "sys.modules",
            {
                "pyrite.services.search_service": MagicMock(
                    SearchService=mock_search_cls
                )
            },
        ):
            results = ctx.search_semantic("test")
            assert results == []

    def test_search_semantic_respects_limit(self):
        """Custom limit is passed through to search service."""
        ctx = self._make_ctx(kb_name="kb")
        ctx.db.vec_available = False

        mock_svc = MagicMock()
        mock_svc.search.return_value = []
        mock_search_cls = MagicMock(return_value=mock_svc)

        with patch.dict(
            "sys.modules",
            {
                "pyrite.services.search_service": MagicMock(
                    SearchService=mock_search_cls
                )
            },
        ):
            ctx.search_semantic("query", limit=5)
            mock_svc.search.assert_called_once_with(
                "query", kb_name="kb", limit=5
            )

    def test_search_semantic_tries_embedding_first(self):
        """When embedding service is available, tries it before FTS."""
        ctx = self._make_ctx(kb_name="kb")
        ctx.db.vec_available = True

        mock_embed_svc = MagicMock()
        mock_embed_svc.search.return_value = [
            {"id": "vec", "title": "Vector Result"}
        ]
        mock_embed_cls = MagicMock(return_value=mock_embed_svc)
        mock_is_available = MagicMock(return_value=True)

        with patch.dict(
            "sys.modules",
            {
                "pyrite.services.embedding_service": MagicMock(
                    EmbeddingService=mock_embed_cls,
                    is_available=mock_is_available,
                )
            },
        ):
            results = ctx.search_semantic("deep meaning")
            assert len(results) == 1
            assert results[0]["id"] == "vec"
            mock_embed_cls.assert_called_once_with(ctx.db)

    def test_search_semantic_falls_through_when_embedding_returns_empty(self):
        """Falls back to FTS when embedding search returns no results."""
        ctx = self._make_ctx(kb_name="kb")
        ctx.db.vec_available = True

        mock_embed_svc = MagicMock()
        mock_embed_svc.search.return_value = []
        mock_embed_cls = MagicMock(return_value=mock_embed_svc)
        mock_is_available = MagicMock(return_value=True)

        mock_fts_svc = MagicMock()
        mock_fts_svc.search.return_value = [
            {"id": "fts", "title": "FTS Result"}
        ]
        mock_search_cls = MagicMock(return_value=mock_fts_svc)

        with patch.dict(
            "sys.modules",
            {
                "pyrite.services.embedding_service": MagicMock(
                    EmbeddingService=mock_embed_cls,
                    is_available=mock_is_available,
                ),
                "pyrite.services.search_service": MagicMock(
                    SearchService=mock_search_cls
                ),
            },
        ):
            results = ctx.search_semantic("query")
            assert len(results) == 1
            assert results[0]["id"] == "fts"

    def test_search_semantic_uses_context_kb_when_none(self):
        """Uses context kb_name when no kb_name parameter given."""
        ctx = self._make_ctx(kb_name="my-kb")
        ctx.db.vec_available = False

        mock_svc = MagicMock()
        mock_svc.search.return_value = []
        mock_search_cls = MagicMock(return_value=mock_svc)

        with patch.dict(
            "sys.modules",
            {
                "pyrite.services.search_service": MagicMock(
                    SearchService=mock_search_cls
                )
            },
        ):
            ctx.search_semantic("query")
            mock_svc.search.assert_called_once_with(
                "query", kb_name="my-kb", limit=10
            )
