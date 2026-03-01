"""Tests for service layer."""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.exceptions import KBReadOnlyError
from pyrite.services import KBService, QueryExpansionService, SearchMode, SearchService
from pyrite.services.query_expansion_service import is_available
from pyrite.storage.database import PyriteDB


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def test_config(temp_dir):
    """Create test configuration."""
    kb_path = temp_dir / "research"
    kb_path.mkdir()
    (kb_path / "actors").mkdir()

    timeline_path = temp_dir / "timeline"
    timeline_path.mkdir()

    return PyriteConfig(
        knowledge_bases=[
            KBConfig(
                name="test-research",
                path=kb_path,
                kb_type=KBType.RESEARCH,
            ),
            KBConfig(
                name="test-timeline",
                path=timeline_path,
                kb_type=KBType.EVENTS,
            ),
        ],
        settings=Settings(index_path=temp_dir / "index.db"),
    )


@pytest.fixture
def test_db(test_config):
    """Create test database."""
    db = PyriteDB(test_config.settings.index_path)
    yield db
    db.close()


class TestSearchService:
    """Tests for SearchService."""

    @pytest.mark.parametrize(
        "input_query, expected",
        [
            ("hello world", "hello world"),
            ("alex-jones", '"alex-jones"'),
            ("alex-jones 2024-01-15", '"alex-jones" "2024-01-15"'),
            ('trump AND "border wall"', 'trump AND "border wall"'),
            ('"alex-jones"', '"alex-jones"'),
            ("trump OR biden", "trump OR biden"),
            ("trump NOT fake", "trump NOT fake"),
            ("--leading-hyphen", '"--leading-hyphen"'),
            ("trailing-", '"trailing-"'),
            ("a-b-c-d", '"a-b-c-d"'),
            ("café résumé", "café résumé"),
            ("hello  world", "hello  world"),
            ("0.6 milestone", '"0.6" milestone'),
            ("test.py", '"test.py"'),
            ("user@example.com", '"user@example.com"'),
            ("path/to/file", '"path/to/file"'),
            ("tag#name", '"tag#name"'),
            ("a:b", '"a:b"'),
            ("hello! world", '"hello!" world'),
        ],
        ids=[
            "simple-passthrough",
            "hyphenated-quoted",
            "multiple-hyphens-quoted",
            "AND-operator-preserved",
            "quoted-phrase-preserved",
            "OR-operator-preserved",
            "NOT-operator-preserved",
            "leading-double-hyphen",
            "trailing-hyphen",
            "multi-hyphen-chain",
            "unicode-passthrough",
            "double-space-passthrough",
            "dot-in-number",
            "dot-in-filename",
            "at-sign-email",
            "slash-in-path",
            "hash-sign",
            "colon-separator",
            "exclamation-mark",
        ],
    )
    def test_sanitize_fts_query(self, input_query, expected):
        """FTS5 query sanitization handles special characters and operators."""
        assert SearchService.sanitize_fts_query(input_query) == expected

    def test_search_normalizes_all_kbs(self, test_db, test_config):
        """'All KBs' is normalized to None."""
        service = SearchService(test_db)
        # This should not raise - it normalizes the kb_name
        results = service.search("test", kb_name="All KBs")
        assert isinstance(results, list)

    def test_search_mode_enum(self):
        """SearchMode enum has expected values."""
        assert SearchMode.KEYWORD.value == "keyword"
        assert SearchMode.SEMANTIC.value == "semantic"
        assert SearchMode.HYBRID.value == "hybrid"

    def test_search_mode_from_string(self):
        """SearchMode can be created from string."""
        assert SearchMode("keyword") == SearchMode.KEYWORD
        assert SearchMode("semantic") == SearchMode.SEMANTIC
        assert SearchMode("hybrid") == SearchMode.HYBRID

    def test_search_with_mode_keyword(self, test_db, test_config):
        """Search with keyword mode works (default path)."""
        service = SearchService(test_db)
        results = service.search("test", mode=SearchMode.KEYWORD)
        assert isinstance(results, list)

    def test_search_with_mode_string(self, test_db, test_config):
        """Search accepts mode as string."""
        service = SearchService(test_db)
        results = service.search("test", mode="keyword")
        assert isinstance(results, list)

    def test_search_hybrid_fallback_no_embeddings(self, test_db, test_config):
        """Hybrid search falls back to keyword when no embeddings exist."""
        service = SearchService(test_db)
        # Hybrid should not raise, just fall back to keyword
        results = service.search("test", mode=SearchMode.HYBRID)
        assert isinstance(results, list)

    def test_search_semantic_no_deps(self, test_db, test_config):
        """Semantic search returns empty when embeddings unavailable."""
        service = SearchService(test_db)
        # Without embeddings, semantic returns empty
        results = service.search("test", mode=SearchMode.SEMANTIC)
        assert isinstance(results, list)

    def test_search_invalid_mode_falls_back(self, test_db, test_config):
        """Invalid mode string falls back to keyword."""
        service = SearchService(test_db)
        results = service.search("test", mode="invalid_mode")
        assert isinstance(results, list)

    def test_hybrid_search_offset_returns_correct_page(self, test_db, test_config):
        """Hybrid search with offset returns the correct page of fused results."""
        from unittest.mock import patch

        service = SearchService(test_db)

        # Create 20 fake keyword results
        keyword_results = [
            {"id": f"kw-{i}", "kb_name": "test", "title": f"Keyword {i}"}
            for i in range(20)
        ]
        # Create 20 fake semantic results (different IDs = 40 unique after fusion)
        semantic_results = [
            {"id": f"sem-{i}", "kb_name": "test", "title": f"Semantic {i}"}
            for i in range(20)
        ]

        with (
            patch.object(test_db, "search", return_value=keyword_results),
            patch.object(service, "_semantic_search", return_value=semantic_results),
        ):
            # Get page 1 (offset=0, limit=5)
            page1 = service.search("test", mode=SearchMode.HYBRID, limit=5, offset=0)
            # Get page 2 (offset=5, limit=5)
            page2 = service.search("test", mode=SearchMode.HYBRID, limit=5, offset=5)
            # Get page 3 (offset=10, limit=5)
            page3 = service.search("test", mode=SearchMode.HYBRID, limit=5, offset=10)

        # Pages should not overlap
        page1_ids = {r["id"] for r in page1}
        page2_ids = {r["id"] for r in page2}
        page3_ids = {r["id"] for r in page3}
        assert page1_ids.isdisjoint(page2_ids), "Page 1 and 2 should not overlap"
        assert page2_ids.isdisjoint(page3_ids), "Page 2 and 3 should not overlap"
        assert page1_ids.isdisjoint(page3_ids), "Page 1 and 3 should not overlap"

        # Each page should have 5 results (40 unique entries in pool)
        assert len(page1) == 5
        assert len(page2) == 5
        assert len(page3) == 5

    def test_hybrid_search_large_offset_fetches_enough(self, test_db, test_config):
        """Hybrid search fetches enough candidates from each leg for large offsets."""
        from unittest.mock import patch

        service = SearchService(test_db)
        offset = 20
        limit = 5

        db_call_args = {}

        def capture_db_search(**kwargs):
            db_call_args.update(kwargs)
            return [
                {"id": f"kw-{i}", "kb_name": "test", "title": f"Keyword {i}"}
                for i in range(kwargs.get("limit", 50))
            ]

        semantic_results = [
            {"id": f"sem-{i}", "kb_name": "test", "title": f"Semantic {i}"}
            for i in range(50)
        ]

        with (
            patch.object(test_db, "search", side_effect=capture_db_search),
            patch.object(service, "_semantic_search", return_value=semantic_results),
        ):
            results = service.search(
                "test", mode=SearchMode.HYBRID, limit=limit, offset=offset
            )

        # Keyword leg should fetch enough to cover offset + limit
        keyword_limit = db_call_args["limit"]
        assert keyword_limit >= offset + limit, (
            f"Keyword leg fetched {keyword_limit} but needs >= {offset + limit} "
            f"to cover offset={offset} + limit={limit}"
        )


class TestKBService:
    """Tests for KBService."""

    def test_list_kbs(self, test_db, test_config):
        """list_kbs returns all configured KBs."""
        service = KBService(test_config, test_db)

        kbs = service.list_kbs()

        assert len(kbs) == 2
        names = {kb["name"] for kb in kbs}
        assert "test-research" in names
        assert "test-timeline" in names

    def test_list_kbs_includes_stats(self, test_db, test_config):
        """list_kbs includes entry counts."""
        service = KBService(test_config, test_db)

        kbs = service.list_kbs()

        for kb in kbs:
            assert "entries" in kb
            assert "indexed" in kb
            assert "type" in kb

    def test_get_kb_found(self, test_db, test_config):
        """get_kb returns config for existing KB."""
        service = KBService(test_config, test_db)

        kb = service.get_kb("test-research")

        assert kb is not None
        assert kb.name == "test-research"

    def test_get_kb_not_found(self, test_db, test_config):
        """get_kb returns None for missing KB."""
        service = KBService(test_config, test_db)

        kb = service.get_kb("nonexistent")

        assert kb is None

    def test_create_entry_research(self, test_db, test_config):
        """create_entry creates research entry."""
        service = KBService(test_config, test_db)

        entry = service.create_entry(
            kb_name="test-research",
            entry_id="test-actor",
            title="Test Actor",
            entry_type="actor",
            body="Test body",
            tags=["test"],
        )

        assert entry.id == "test-actor"
        assert entry.title == "Test Actor"

    def test_create_entry_event(self, test_db, test_config):
        """create_entry creates event entry."""
        service = KBService(test_config, test_db)

        entry = service.create_entry(
            kb_name="test-timeline",
            entry_id="test-event",
            title="Test Event",
            entry_type="event",
            date="2024-01-15",
            importance=4,
        )

        assert entry.id == "test-event"
        assert entry.date == "2024-01-15"

    def test_create_entry_read_only_fails(self, test_db, temp_dir):
        """create_entry fails on read-only KB."""
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(
                    name="readonly-kb",
                    path=temp_dir / "readonly",
                    kb_type=KBType.RESEARCH,
                    read_only=True,
                ),
            ],
            settings=Settings(index_path=temp_dir / "index.db"),
        )
        (temp_dir / "readonly").mkdir()

        service = KBService(config, test_db)

        with pytest.raises(KBReadOnlyError, match="read-only"):
            service.create_entry(
                kb_name="readonly-kb",
                entry_id="test",
                title="Test",
                entry_type="actor",
            )

    def test_get_entry(self, test_db, test_config):
        """get_entry retrieves created entry."""
        service = KBService(test_config, test_db)

        # Create an entry
        service.create_entry(
            kb_name="test-research",
            entry_id="get-test",
            title="Get Test",
            entry_type="actor",
        )

        # Retrieve it
        entry = service.get_entry("get-test", "test-research")

        assert entry is not None
        assert entry["title"] == "Get Test"

    def test_get_entry_searches_all_kbs(self, test_db, test_config):
        """get_entry without kb_name searches all KBs."""
        service = KBService(test_config, test_db)

        service.create_entry(
            kb_name="test-research",
            entry_id="search-all-test",
            title="Search All Test",
            entry_type="actor",
        )

        # Search without specifying KB
        entry = service.get_entry("search-all-test")

        assert entry is not None
        assert entry["title"] == "Search All Test"

    def test_delete_entry(self, test_db, test_config):
        """delete_entry removes entry from file and index."""
        service = KBService(test_config, test_db)

        service.create_entry(
            kb_name="test-research",
            entry_id="delete-test",
            title="Delete Test",
            entry_type="actor",
        )

        result = service.delete_entry("delete-test", "test-research")

        assert result is True
        assert service.get_entry("delete-test", "test-research") is None


class TestQueryExpansionService:
    """Tests for QueryExpansionService."""

    def test_stub_provider_returns_empty(self):
        """Stub provider returns empty list."""
        svc = QueryExpansionService(provider="stub")
        assert svc.expand("immigration policy") == []

    def test_none_provider_returns_empty(self):
        """None provider returns empty list."""
        svc = QueryExpansionService(provider="none")
        assert svc.expand("immigration policy") == []

    def test_empty_query_returns_empty(self):
        """Empty query returns empty list."""
        svc = QueryExpansionService(provider="anthropic")
        assert svc.expand("") == []
        assert svc.expand("   ") == []

    def test_unavailable_provider_returns_empty(self):
        """Unavailable/unknown provider returns empty list."""
        svc = QueryExpansionService(provider="nonexistent_provider_xyz")
        assert svc.expand("immigration policy") == []

    def test_is_available_stub(self):
        """is_available returns True for stub/none."""
        assert is_available("stub") is True
        assert is_available("none") is True
        assert is_available("") is True

    def test_is_available_unknown(self):
        """is_available returns False for unknown provider."""
        assert is_available("nonexistent_provider_xyz") is False

    def test_parse_terms_basic(self):
        """_parse_terms handles basic multi-line output."""
        terms = QueryExpansionService._parse_terms("term one\nterm two\nterm three")
        assert terms == ["term one", "term two", "term three"]

    def test_parse_terms_strips_bullets(self):
        """_parse_terms strips bullet/numbering prefixes."""
        terms = QueryExpansionService._parse_terms("- term one\n1. term two\n* term three")
        assert terms == ["term one", "term two", "term three"]

    def test_parse_terms_respects_max(self):
        """_parse_terms limits to MAX_TERMS."""
        lines = "\n".join(f"term {i}" for i in range(20))
        terms = QueryExpansionService._parse_terms(lines)
        assert len(terms) <= 10

    def test_parse_terms_filters_long(self):
        """_parse_terms skips terms longer than MAX_TERM_LENGTH."""
        terms = QueryExpansionService._parse_terms("short\n" + "x" * 100)
        assert terms == ["short"]

    def test_search_with_expand_stub_works(self, test_db, test_config):
        """SearchService with expand=True + stub provider works (no-op expansion)."""
        service = SearchService(test_db, settings=test_config.settings)
        results = service.search("test", expand=True)
        assert isinstance(results, list)

    def test_search_expand_without_settings(self, test_db):
        """SearchService with expand=True but no settings returns normal results."""
        service = SearchService(test_db)
        results = service.search("test", expand=True)
        assert isinstance(results, list)
