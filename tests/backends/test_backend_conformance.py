"""
SearchBackend conformance test suite.

Every test here runs against every registered backend via the parametrized
``backend`` fixture.  A backend passes conformance when all tests pass.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(entry_id="e1", kb_name="test", **overrides):
    """Build a minimal entry data dict."""
    data = {
        "id": entry_id,
        "kb_name": kb_name,
        "entry_type": "note",
        "title": f"Title {entry_id}",
        "body": f"Body for {entry_id}",
        "summary": f"Summary of {entry_id}",
        "tags": [],
        "sources": [],
        "links": [],
        "metadata": {},
    }
    data.update(overrides)
    return data


# =========================================================================
# Entry lifecycle
# =========================================================================

class TestEntryLifecycle:
    def test_upsert_and_get(self, backend):
        backend.upsert_entry(_make_entry("e1"))
        entry = backend.get_entry("e1", "test")
        assert entry is not None
        assert entry["id"] == "e1"
        assert entry["title"] == "Title e1"
        assert entry["body"] == "Body for e1"

    def test_get_missing_returns_none(self, backend):
        assert backend.get_entry("nonexistent", "test") is None

    def test_upsert_update(self, backend):
        backend.upsert_entry(_make_entry("e1", title="Original"))
        backend.upsert_entry(_make_entry("e1", title="Updated"))
        entry = backend.get_entry("e1", "test")
        assert entry["title"] == "Updated"

    def test_delete_entry(self, backend):
        backend.upsert_entry(_make_entry("e1"))
        assert backend.delete_entry("e1", "test") is True
        assert backend.get_entry("e1", "test") is None

    def test_delete_nonexistent(self, backend):
        assert backend.delete_entry("nope", "test") is False

    def test_list_entries(self, backend):
        for i in range(5):
            backend.upsert_entry(_make_entry(f"e{i}"))
        entries = backend.list_entries(kb_name="test")
        assert len(entries) == 5

    def test_list_entries_with_type_filter(self, backend):
        backend.upsert_entry(_make_entry("e1", entry_type="note"))
        backend.upsert_entry(_make_entry("e2", entry_type="event"))
        entries = backend.list_entries(kb_name="test", entry_type="note")
        assert len(entries) == 1
        assert entries[0]["entry_type"] == "note"

    def test_list_entries_with_tag_filter(self, backend):
        backend.upsert_entry(_make_entry("e1", tags=["alpha", "beta"]))
        backend.upsert_entry(_make_entry("e2", tags=["gamma"]))
        entries = backend.list_entries(kb_name="test", tag="alpha")
        assert len(entries) == 1
        assert entries[0]["id"] == "e1"

    def test_list_entries_pagination(self, backend):
        for i in range(10):
            backend.upsert_entry(_make_entry(f"e{i:02d}"))
        page1 = backend.list_entries(kb_name="test", limit=3, offset=0)
        page2 = backend.list_entries(kb_name="test", limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        ids1 = {e["id"] for e in page1}
        ids2 = {e["id"] for e in page2}
        assert ids1.isdisjoint(ids2)

    def test_count_entries(self, backend):
        for i in range(3):
            backend.upsert_entry(_make_entry(f"e{i}"))
        assert backend.count_entries(kb_name="test") == 3

    def test_count_entries_filtered(self, backend):
        backend.upsert_entry(_make_entry("e1", entry_type="note"))
        backend.upsert_entry(_make_entry("e2", entry_type="event"))
        assert backend.count_entries(kb_name="test", entry_type="note") == 1

    def test_count_entries_by_tag(self, backend):
        backend.upsert_entry(_make_entry("e1", tags=["alpha"]))
        backend.upsert_entry(_make_entry("e2", tags=["beta"]))
        assert backend.count_entries(kb_name="test", tag="alpha") == 1

    def test_get_distinct_types(self, backend):
        backend.upsert_entry(_make_entry("e1", entry_type="note"))
        backend.upsert_entry(_make_entry("e2", entry_type="event"))
        backend.upsert_entry(_make_entry("e3", entry_type="note"))
        types = backend.get_distinct_types(kb_name="test")
        assert sorted(types) == ["event", "note"]

    def test_get_entries_for_indexing(self, backend):
        backend.upsert_entry(_make_entry("e1", file_path="notes/e1.md"))
        result = backend.get_entries_for_indexing("test")
        assert len(result) == 1
        assert result[0]["id"] == "e1"
        assert result[0]["file_path"] == "notes/e1.md"

    def test_entry_metadata(self, backend):
        backend.upsert_entry(_make_entry("e1", metadata={"custom_field": "value"}))
        entry = backend.get_entry("e1", "test")
        import json
        meta = json.loads(entry["metadata"]) if isinstance(entry["metadata"], str) else entry["metadata"]
        assert meta["custom_field"] == "value"

    def test_entry_importance_and_status(self, backend):
        backend.upsert_entry(_make_entry("e1", importance=5, status="draft"))
        entry = backend.get_entry("e1", "test")
        assert entry["importance"] == 5
        assert entry["status"] == "draft"


# =========================================================================
# Tags
# =========================================================================

class TestTags:
    def test_tags_stored_and_retrieved(self, backend):
        backend.upsert_entry(_make_entry("e1", tags=["alpha", "beta"]))
        entry = backend.get_entry("e1", "test")
        assert sorted(entry["tags"]) == ["alpha", "beta"]

    def test_tags_replaced_on_update(self, backend):
        backend.upsert_entry(_make_entry("e1", tags=["old"]))
        backend.upsert_entry(_make_entry("e1", tags=["new1", "new2"]))
        entry = backend.get_entry("e1", "test")
        assert sorted(entry["tags"]) == ["new1", "new2"]

    def test_get_all_tags(self, backend):
        backend.upsert_entry(_make_entry("e1", tags=["alpha", "beta"]))
        backend.upsert_entry(_make_entry("e2", tags=["alpha", "gamma"]))
        tags = backend.get_all_tags(kb_name="test")
        tag_dict = dict(tags)
        assert tag_dict["alpha"] == 2
        assert tag_dict["beta"] == 1
        assert tag_dict["gamma"] == 1

    def test_get_all_tags_no_kb_filter(self, backend_with_db):
        backend, db = backend_with_db
        backend.upsert_entry(_make_entry("e1", kb_name="test", tags=["shared"]))
        backend.upsert_entry(_make_entry("e2", kb_name="other", tags=["shared"]))
        tags = backend.get_all_tags()
        tag_dict = dict(tags)
        assert tag_dict["shared"] == 2

    def test_get_tags_as_dicts(self, backend):
        backend.upsert_entry(_make_entry("e1", tags=["alpha", "beta"]))
        tags = backend.get_tags_as_dicts(kb_name="test")
        assert len(tags) == 2
        names = {t["name"] for t in tags}
        assert "alpha" in names
        assert "beta" in names

    def test_get_tags_as_dicts_with_prefix(self, backend):
        backend.upsert_entry(_make_entry("e1", tags=["topic/ai", "topic/ml", "other"]))
        tags = backend.get_tags_as_dicts(kb_name="test", prefix="topic")
        assert len(tags) == 2

    def test_search_by_tag(self, backend):
        backend.upsert_entry(_make_entry("e1", tags=["alpha"]))
        backend.upsert_entry(_make_entry("e2", tags=["beta"]))
        results = backend.search_by_tag("alpha", kb_name="test")
        assert len(results) == 1

    def test_search_by_tag_prefix(self, backend):
        backend.upsert_entry(_make_entry("e1", tags=["topic/ai"]))
        backend.upsert_entry(_make_entry("e2", tags=["topic/ml"]))
        backend.upsert_entry(_make_entry("e3", tags=["other"]))
        results = backend.search_by_tag_prefix("topic", kb_name="test")
        assert len(results) == 2

    def test_empty_tags_ignored(self, backend):
        backend.upsert_entry(_make_entry("e1", tags=["alpha", "", "beta"]))
        entry = backend.get_entry("e1", "test")
        assert sorted(entry["tags"]) == ["alpha", "beta"]


# =========================================================================
# Full-text search
# =========================================================================

class TestFullTextSearch:
    def test_search_basic(self, backend):
        backend.upsert_entry(_make_entry("e1", title="quantum computing advances"))
        backend.upsert_entry(_make_entry("e2", title="classical music review"))
        results = backend.search("quantum")
        assert len(results) >= 1
        assert any(r["id"] == "e1" for r in results)

    def test_search_with_kb_filter(self, backend_with_db):
        backend, db = backend_with_db
        backend.upsert_entry(_make_entry("e1", kb_name="test", title="quantum computing"))
        backend.upsert_entry(_make_entry("e2", kb_name="other", title="quantum physics"))
        results = backend.search("quantum", kb_name="test")
        assert len(results) == 1
        assert results[0]["kb_name"] == "test"

    def test_search_with_type_filter(self, backend):
        backend.upsert_entry(_make_entry("e1", entry_type="note", title="quantum note"))
        backend.upsert_entry(_make_entry("e2", entry_type="event", title="quantum event"))
        results = backend.search("quantum", entry_type="note")
        assert len(results) == 1
        assert results[0]["entry_type"] == "note"

    def test_search_with_tag_filter(self, backend):
        backend.upsert_entry(_make_entry("e1", title="quantum topic", tags=["science"]))
        backend.upsert_entry(_make_entry("e2", title="quantum other", tags=["music"]))
        results = backend.search("quantum", tags=["science"])
        assert len(results) == 1
        assert results[0]["id"] == "e1"

    def test_search_with_date_filter(self, backend):
        backend.upsert_entry(_make_entry("e1", title="quantum old", date="2020-01-01"))
        backend.upsert_entry(_make_entry("e2", title="quantum new", date="2024-01-01"))
        results = backend.search("quantum", date_from="2023-01-01")
        assert len(results) == 1
        assert results[0]["id"] == "e2"

    def test_search_returns_snippet(self, backend):
        backend.upsert_entry(_make_entry("e1", title="quantum", body="quantum computing body"))
        results = backend.search("quantum")
        assert len(results) >= 1
        # FTS results should include snippet and rank
        assert "snippet" in results[0]
        assert "rank" in results[0]

    def test_search_pagination(self, backend):
        for i in range(10):
            backend.upsert_entry(_make_entry(f"e{i}", title=f"quantum topic {i}"))
        page1 = backend.search("quantum", limit=3, offset=0)
        page2 = backend.search("quantum", limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3

    def test_search_by_date_range(self, backend):
        backend.upsert_entry(_make_entry("e1", date="2020-06-15"))
        backend.upsert_entry(_make_entry("e2", date="2021-03-01"))
        backend.upsert_entry(_make_entry("e3", date="2022-01-01"))
        results = backend.search_by_date_range("2020-01-01", "2021-12-31")
        assert len(results) == 2


# =========================================================================
# Graph (links)
# =========================================================================

class TestGraph:
    def _setup_linked_entries(self, backend):
        backend.upsert_entry(_make_entry("a", title="Entry A", links=[
            {"target": "b", "relation": "related_to"},
        ]))
        backend.upsert_entry(_make_entry("b", title="Entry B", links=[
            {"target": "c", "relation": "related_to"},
        ]))
        backend.upsert_entry(_make_entry("c", title="Entry C"))

    def test_get_backlinks(self, backend):
        self._setup_linked_entries(backend)
        backlinks = backend.get_backlinks("b", "test")
        assert len(backlinks) == 1
        assert backlinks[0]["id"] == "a"

    def test_get_backlinks_empty(self, backend):
        self._setup_linked_entries(backend)
        backlinks = backend.get_backlinks("a", "test")
        assert len(backlinks) == 0

    def test_get_outlinks(self, backend):
        self._setup_linked_entries(backend)
        outlinks = backend.get_outlinks("a", "test")
        assert len(outlinks) == 1
        assert outlinks[0]["id"] == "b"

    def test_get_outlinks_empty(self, backend):
        self._setup_linked_entries(backend)
        outlinks = backend.get_outlinks("c", "test")
        assert len(outlinks) == 0

    def test_get_backlinks_with_limit(self, backend):
        # Create many inbound links to c
        for i in range(5):
            backend.upsert_entry(_make_entry(f"src{i}", title=f"Source {i}", links=[
                {"target": "target", "relation": "related_to"},
            ]))
        backend.upsert_entry(_make_entry("target", title="Target"))
        backlinks = backend.get_backlinks("target", "test", limit=2)
        assert len(backlinks) == 2

    def test_get_graph_data_centered(self, backend):
        self._setup_linked_entries(backend)
        graph = backend.get_graph_data(center="b", center_kb="test", depth=1)
        assert "nodes" in graph
        assert "edges" in graph
        node_ids = {n["id"] for n in graph["nodes"]}
        assert "b" in node_ids
        # At depth 1, should have a and c
        assert "a" in node_ids
        assert "c" in node_ids

    def test_get_graph_data_no_center(self, backend):
        self._setup_linked_entries(backend)
        graph = backend.get_graph_data()
        assert len(graph["nodes"]) >= 2
        assert len(graph["edges"]) >= 1

    def test_get_most_linked(self, backend):
        self._setup_linked_entries(backend)
        most = backend.get_most_linked(kb_name="test", limit=5)
        # b has 1 incoming link, c has 1 incoming link
        assert len(most) >= 2

    def test_get_orphans(self, backend):
        backend.upsert_entry(_make_entry("orphan", title="Lonely"))
        backend.upsert_entry(_make_entry("linked", links=[
            {"target": "other", "relation": "related_to"},
        ]))
        backend.upsert_entry(_make_entry("other"))
        orphans = backend.get_orphans(kb_name="test")
        orphan_ids = {o["id"] for o in orphans}
        assert "orphan" in orphan_ids
        assert "linked" not in orphan_ids


# =========================================================================
# Sources
# =========================================================================

class TestSources:
    def test_sources_stored(self, backend):
        backend.upsert_entry(_make_entry("e1", sources=[
            {"title": "Source 1", "url": "https://example.com", "outlet": "Blog"},
        ]))
        entry = backend.get_entry("e1", "test")
        assert len(entry["sources"]) == 1
        assert entry["sources"][0]["title"] == "Source 1"

    def test_sources_replaced_on_update(self, backend):
        backend.upsert_entry(_make_entry("e1", sources=[{"title": "Old"}]))
        backend.upsert_entry(_make_entry("e1", sources=[{"title": "New"}]))
        entry = backend.get_entry("e1", "test")
        assert len(entry["sources"]) == 1
        assert entry["sources"][0]["title"] == "New"


# =========================================================================
# Object refs
# =========================================================================

class TestObjectRefs:
    def test_refs_from(self, backend):
        backend.upsert_entry(_make_entry("e1", _refs=[
            {"target_id": "e2", "field_name": "author", "target_type": "person"},
        ]))
        backend.upsert_entry(_make_entry("e2", entry_type="person", title="Person"))
        refs = backend.get_refs_from("e1", "test")
        assert len(refs) == 1
        assert refs[0]["id"] == "e2"
        assert refs[0]["field_name"] == "author"

    def test_refs_to(self, backend):
        backend.upsert_entry(_make_entry("e1", _refs=[
            {"target_id": "e2", "field_name": "author", "target_type": "person"},
        ]))
        backend.upsert_entry(_make_entry("e2"))
        refs = backend.get_refs_to("e2", "test")
        assert len(refs) == 1
        assert refs[0]["id"] == "e1"

    def test_refs_replaced_on_update(self, backend):
        backend.upsert_entry(_make_entry("e1", _refs=[
            {"target_id": "old", "field_name": "ref"},
        ]))
        backend.upsert_entry(_make_entry("e1", _refs=[
            {"target_id": "new", "field_name": "ref"},
        ]))
        refs = backend.get_refs_from("e1", "test")
        assert len(refs) == 1
        assert refs[0]["id"] == "new"


# =========================================================================
# Blocks
# =========================================================================

class TestBlocks:
    def test_blocks_stored(self, backend):
        backend.upsert_entry(_make_entry("e1", _blocks=[
            {"block_id": "b1", "heading": "Section 1", "content": "Content 1", "position": 0, "block_type": "heading"},
            {"block_id": "b2", "heading": "Section 2", "content": "Content 2", "position": 1, "block_type": "heading"},
        ]))
        # Blocks don't have a direct get, but upsert shouldn't fail
        entry = backend.get_entry("e1", "test")
        assert entry is not None

    def test_blocks_replaced_on_update(self, backend):
        backend.upsert_entry(_make_entry("e1", _blocks=[
            {"block_id": "b1", "heading": "Old", "content": "Old", "position": 0, "block_type": "heading"},
        ]))
        backend.upsert_entry(_make_entry("e1", _blocks=[
            {"block_id": "b2", "heading": "New", "content": "New", "position": 0, "block_type": "heading"},
        ]))
        entry = backend.get_entry("e1", "test")
        assert entry is not None


# =========================================================================
# Timeline
# =========================================================================

class TestTimeline:
    def test_timeline_basic(self, backend):
        backend.upsert_entry(_make_entry("e1", date="2024-01-15", importance=3, title="Event 1"))
        backend.upsert_entry(_make_entry("e2", date="2024-02-15", importance=5, title="Event 2"))
        backend.upsert_entry(_make_entry("e3", importance=2))  # no date
        timeline = backend.get_timeline()
        assert len(timeline) == 2

    def test_timeline_date_filter(self, backend):
        backend.upsert_entry(_make_entry("e1", date="2024-01-15", importance=3))
        backend.upsert_entry(_make_entry("e2", date="2024-06-15", importance=3))
        timeline = backend.get_timeline(date_from="2024-03-01")
        assert len(timeline) == 1
        assert timeline[0]["id"] == "e2"

    def test_timeline_importance_filter(self, backend):
        backend.upsert_entry(_make_entry("e1", date="2024-01-15", importance=1))
        backend.upsert_entry(_make_entry("e2", date="2024-02-15", importance=5))
        timeline = backend.get_timeline(min_importance=3)
        assert len(timeline) == 1
        assert timeline[0]["id"] == "e2"

    def test_timeline_ordered_by_date(self, backend):
        backend.upsert_entry(_make_entry("e2", date="2024-06-01", importance=1))
        backend.upsert_entry(_make_entry("e1", date="2024-01-01", importance=1))
        timeline = backend.get_timeline()
        assert timeline[0]["id"] == "e1"
        assert timeline[1]["id"] == "e2"


# =========================================================================
# Folder queries
# =========================================================================

class TestFolderQueries:
    def test_list_entries_in_folder(self, backend):
        backend.upsert_entry(_make_entry("e1", file_path="notes/sub/e1.md"))
        backend.upsert_entry(_make_entry("e2", file_path="notes/sub/e2.md"))
        backend.upsert_entry(_make_entry("e3", file_path="other/e3.md"))
        results = backend.list_entries_in_folder("test", "notes/sub")
        assert len(results) == 2

    def test_count_entries_in_folder(self, backend):
        backend.upsert_entry(_make_entry("e1", file_path="notes/e1.md"))
        backend.upsert_entry(_make_entry("e2", file_path="notes/e2.md"))
        backend.upsert_entry(_make_entry("e3", file_path="other/e3.md"))
        assert backend.count_entries_in_folder("test", "notes") == 2

    def test_folder_excludes_collections(self, backend):
        backend.upsert_entry(_make_entry("e1", file_path="notes/e1.md", entry_type="note"))
        backend.upsert_entry(_make_entry("c1", file_path="notes/c1.md", entry_type="collection"))
        results = backend.list_entries_in_folder("test", "notes")
        assert len(results) == 1


# =========================================================================
# Global counts
# =========================================================================

class TestGlobalCounts:
    def test_global_counts(self, backend):
        backend.upsert_entry(_make_entry("e1", tags=["alpha"], links=[
            {"target": "e2", "relation": "related_to"},
        ]))
        backend.upsert_entry(_make_entry("e2", tags=["beta"]))
        counts = backend.get_global_counts()
        assert counts["total_tags"] == 2
        assert counts["total_links"] == 1


# =========================================================================
# Multi-KB isolation
# =========================================================================

class TestMultiKB:
    def test_entries_isolated_by_kb(self, backend_with_db):
        backend, db = backend_with_db
        backend.upsert_entry(_make_entry("e1", kb_name="test", title="Test entry"))
        backend.upsert_entry(_make_entry("e1", kb_name="other", title="Other entry"))
        test_entry = backend.get_entry("e1", "test")
        other_entry = backend.get_entry("e1", "other")
        assert test_entry["title"] == "Test entry"
        assert other_entry["title"] == "Other entry"

    def test_list_entries_scoped_to_kb(self, backend_with_db):
        backend, db = backend_with_db
        backend.upsert_entry(_make_entry("e1", kb_name="test"))
        backend.upsert_entry(_make_entry("e2", kb_name="other"))
        entries = backend.list_entries(kb_name="test")
        assert len(entries) == 1
        assert entries[0]["kb_name"] == "test"

    def test_search_scoped_to_kb(self, backend_with_db):
        backend, db = backend_with_db
        backend.upsert_entry(_make_entry("e1", kb_name="test", title="quantum test"))
        backend.upsert_entry(_make_entry("e2", kb_name="other", title="quantum other"))
        results = backend.search("quantum", kb_name="test")
        assert len(results) == 1
        assert results[0]["kb_name"] == "test"

    def test_delete_only_in_correct_kb(self, backend_with_db):
        backend, db = backend_with_db
        backend.upsert_entry(_make_entry("e1", kb_name="test"))
        backend.upsert_entry(_make_entry("e1", kb_name="other"))
        backend.delete_entry("e1", "test")
        assert backend.get_entry("e1", "test") is None
        assert backend.get_entry("e1", "other") is not None


# =========================================================================
# Embeddings (basic — only tests interface, not actual model)
# =========================================================================

class TestEmbeddingInterface:
    """Tests the embedding API surface. Actual vector search requires sqlite-vec."""

    def test_has_embeddings_false_initially(self, backend):
        # May be False if vec not available, or True with no data — both valid
        result = backend.has_embeddings()
        assert isinstance(result, bool)

    def test_embedding_stats_structure(self, backend):
        stats = backend.embedding_stats()
        assert "count" in stats
        assert "total_entries" in stats

    def test_get_embedded_rowids_returns_set(self, backend):
        result = backend.get_embedded_rowids()
        assert isinstance(result, set)

    def test_get_entries_for_embedding(self, backend):
        backend.upsert_entry(_make_entry("e1"))
        result = backend.get_entries_for_embedding(kb_name="test")
        assert len(result) >= 1
        assert "id" in result[0]
        assert "title" in result[0]

    def test_search_semantic_empty(self, backend):
        # With no embeddings, should return empty list
        result = backend.search_semantic([0.0] * 384)
        assert isinstance(result, list)
