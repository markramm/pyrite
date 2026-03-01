"""Performance tests for 1000+ entry knowledge bases.

Run with: pytest tests/test_performance.py -v -m slow
Skip in CI: pytest -m "not slow"
"""

import random
import tempfile
import time
from pathlib import Path

import pytest

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import NoteEntry, EventEntry
from pyrite.services.kb_service import KBService
from pyrite.services.qa_service import QAService
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_ENTRIES = 1050

TAG_POOL = [
    "python", "rust", "javascript", "architecture", "database",
    "api", "testing", "security", "performance", "devops",
    "frontend", "backend", "infra", "ml", "data",
    "design", "refactor", "bugfix", "feature", "docs",
]

TOPIC_WORDS = [
    "indexing", "caching", "routing", "authentication", "pagination",
    "migration", "deployment", "monitoring", "logging", "serialization",
    "validation", "concurrency", "throughput", "latency", "resilience",
    "scalability", "observability", "orchestration", "federation", "replication",
]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def large_kb():
    """Create a 1000+ entry KB with mixed types, tags, and inter-entry links."""
    rng = random.Random(42)  # deterministic seed

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"

        notes_path = tmpdir / "notes"
        notes_path.mkdir()

        kb_config = KBConfig(
            name="perf-test",
            path=notes_path,
            kb_type=KBType.GENERIC,
        )

        config = PyriteConfig(
            knowledge_bases=[kb_config],
            settings=Settings(index_path=db_path),
        )

        repo = KBRepository(kb_config)

        # Pre-generate all entry IDs for linking
        entry_ids = [f"entry-{i:04d}" for i in range(NUM_ENTRIES)]

        # Create entries — 80% notes, 20% events
        for i, eid in enumerate(entry_ids):
            topic = TOPIC_WORDS[i % len(TOPIC_WORDS)]
            tags = rng.sample(TAG_POOL, k=rng.randint(1, 4))

            if i % 5 == 0:
                # Event entry (20%)
                entry = EventEntry(
                    id=eid,
                    title=f"Event {i}: {topic.capitalize()} milestone",
                    body=(
                        f"This event covers the {topic} milestone. "
                        f"It involves significant progress on {topic} across "
                        f"multiple subsystems. Details include planning, "
                        f"execution, and retrospective analysis of {topic}."
                    ),
                    date=f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                    importance=rng.randint(1, 10),
                )
            else:
                # Note entry (80%)
                entry = NoteEntry(
                    id=eid,
                    title=f"Note {i}: Topic about {topic}",
                    body=(
                        f"This note discusses {topic} in depth. "
                        f"Key considerations include performance, "
                        f"maintainability, and correctness of {topic}. "
                        f"Related areas: {', '.join(tags)}."
                    ),
                )

            entry.tags = tags

            # ~10% of entries link to 2-3 others
            if rng.random() < 0.10:
                targets = rng.sample(
                    [e for e in entry_ids if e != eid],
                    k=rng.randint(2, 3),
                )
                for t in targets:
                    entry.add_link(target=t, relation="related_to", kb="perf-test")

            repo.save(entry)

        # Build index
        db = PyriteDB(db_path)
        index_mgr = IndexManager(db, config)
        index_mgr.index_all()

        yield {
            "config": config,
            "db": db,
            "kb_config": kb_config,
            "index_mgr": index_mgr,
        }

        db.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPerformance:
    """Performance tests for large knowledge bases."""

    def test_index_sync_performance(self, large_kb):
        """Full re-index of 1000+ entries completes within 30 seconds."""
        index_mgr = large_kb["index_mgr"]

        start = time.perf_counter()
        index_mgr.index_all()
        elapsed = time.perf_counter() - start

        assert elapsed < 30, f"index_all() took {elapsed:.2f}s (limit: 30s)"

    def test_fts_search_performance(self, large_kb):
        """FTS search returns within 500ms; average of 10 searches is acceptable."""
        db = large_kb["db"]
        search_terms = [
            "indexing", "caching", "routing", "authentication", "pagination",
            "migration", "deployment", "monitoring", "logging", "serialization",
        ]

        timings = []
        for term in search_terms:
            start = time.perf_counter()
            results = db.search(term, kb_name="perf-test", limit=50)
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
            # Each individual search should be fast
            assert elapsed < 0.5, (
                f"search('{term}') took {elapsed:.3f}s (limit: 0.5s)"
            )
            # Sanity: we should find results for these terms
            assert len(results) > 0, f"search('{term}') returned no results"

        avg = sum(timings) / len(timings)
        assert avg < 0.5, f"Average search time {avg:.3f}s exceeds 500ms"

    def test_entry_list_performance(self, large_kb):
        """Entry listing with pagination completes within 200ms."""
        config = large_kb["config"]
        db = large_kb["db"]
        svc = KBService(config, db)

        # First page
        start = time.perf_counter()
        page1 = svc.list_entries(kb_name="perf-test", limit=50, offset=0)
        elapsed_first = time.perf_counter() - start
        assert elapsed_first < 0.2, (
            f"list_entries(offset=0) took {elapsed_first:.3f}s (limit: 0.2s)"
        )
        assert len(page1) == 50

        # Mid-range page
        start = time.perf_counter()
        page_mid = svc.list_entries(kb_name="perf-test", limit=50, offset=500)
        elapsed_mid = time.perf_counter() - start
        assert elapsed_mid < 0.2, (
            f"list_entries(offset=500) took {elapsed_mid:.3f}s (limit: 0.2s)"
        )
        assert len(page_mid) == 50

    def test_graph_performance(self, large_kb):
        """Graph retrieval for 1000+ nodes completes within 5 seconds."""
        config = large_kb["config"]
        db = large_kb["db"]
        svc = KBService(config, db)

        start = time.perf_counter()
        graph = svc.get_graph(kb_name="perf-test", limit=1500)
        elapsed = time.perf_counter() - start

        assert elapsed < 5, f"get_graph() took {elapsed:.2f}s (limit: 5s)"
        assert len(graph.get("nodes", [])) > 0, "Graph returned no nodes"

    def test_graph_api_with_centrality_performance(self, large_kb):
        """Graph API with centrality on 1000+ nodes completes within 5 seconds."""
        fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient
        from pyrite.server.api import create_app
        import pyrite.server.api as api_module

        config = large_kb["config"]
        db = large_kb["db"]
        index_mgr = large_kb["index_mgr"]

        api_module._config = config
        api_module._db = db
        api_module._index_mgr = index_mgr

        try:
            app = create_app(config)
            client = TestClient(app)

            start = time.perf_counter()
            response = client.get("/api/graph?include_centrality=true")
            elapsed = time.perf_counter() - start

            assert response.status_code == 200
            data = response.json()
            assert len(data.get("nodes", [])) > 0
            assert elapsed < 5, (
                f"Graph API with centrality took {elapsed:.2f}s (limit: 5s)"
            )
        finally:
            api_module._config = None
            api_module._db = None
            api_module._index_mgr = None

    def test_qa_validate_performance(self, large_kb):
        """QA validation of 1000+ entries completes within 10 seconds."""
        config = large_kb["config"]
        db = large_kb["db"]
        qa_svc = QAService(config, db)

        start = time.perf_counter()
        result = qa_svc.validate_kb("perf-test")
        elapsed = time.perf_counter() - start

        assert elapsed < 10, (
            f"validate_kb() took {elapsed:.2f}s (limit: 10s)"
        )
        assert result["total"] >= 1000, (
            f"Expected 1000+ entries, got {result['total']}"
        )
        assert result["kb_name"] == "perf-test"
