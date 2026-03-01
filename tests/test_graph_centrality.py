"""
Tests for graph betweenness centrality computation.
"""

import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import NoteEntry
from pyrite.server.api import create_app
from pyrite.server.endpoints.graph import compute_betweenness_centrality
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository


# =============================================================================
# Unit tests for the centrality algorithm
# =============================================================================


class TestBetweennessCentrality:
    """Test the BFS-based betweenness centrality algorithm."""

    def test_empty_graph(self):
        """Empty graph returns empty dict."""
        result = compute_betweenness_centrality([], [])
        assert result == {}

    def test_single_node(self):
        """Single node with no edges has 0 centrality."""
        nodes = [{"id": "a", "kb_name": "k"}]
        result = compute_betweenness_centrality(nodes, [])
        assert result[("a", "k")] == 0.0

    def test_two_nodes(self):
        """Two connected nodes: normalization denominator is 0, so centrality is 0."""
        nodes = [{"id": "a", "kb_name": "k"}, {"id": "b", "kb_name": "k"}]
        edges = [{"source_id": "a", "source_kb": "k", "target_id": "b", "target_kb": "k"}]
        result = compute_betweenness_centrality(nodes, edges)
        assert result[("a", "k")] == 0.0
        assert result[("b", "k")] == 0.0

    def test_star_graph(self):
        """Star graph: center node has highest betweenness centrality.

        Graph:  b - a - c
                    |
                    d

        All shortest paths between b,c,d go through a.
        """
        nodes = [
            {"id": "a", "kb_name": "k"},
            {"id": "b", "kb_name": "k"},
            {"id": "c", "kb_name": "k"},
            {"id": "d", "kb_name": "k"},
        ]
        edges = [
            {"source_id": "a", "source_kb": "k", "target_id": "b", "target_kb": "k"},
            {"source_id": "a", "source_kb": "k", "target_id": "c", "target_kb": "k"},
            {"source_id": "a", "source_kb": "k", "target_id": "d", "target_kb": "k"},
        ]
        result = compute_betweenness_centrality(nodes, edges)
        # Center a should have centrality 1.0 (all 3 pairs go through it)
        assert result[("a", "k")] == 1.0
        # Leaf nodes should have centrality 0.0
        assert result[("b", "k")] == 0.0
        assert result[("c", "k")] == 0.0
        assert result[("d", "k")] == 0.0

    def test_path_graph(self):
        """Path graph: middle nodes have highest betweenness centrality.

        Graph: a - b - c - d - e

        Node b is on paths: (a,c), (a,d), (a,e) = 3
        Node c is on paths: (a,d), (a,e), (b,d), (b,e) = 4
        Node d is on paths: (a,e), (b,e), (c,e) = 3
        """
        nodes = [
            {"id": "a", "kb_name": "k"},
            {"id": "b", "kb_name": "k"},
            {"id": "c", "kb_name": "k"},
            {"id": "d", "kb_name": "k"},
            {"id": "e", "kb_name": "k"},
        ]
        edges = [
            {"source_id": "a", "source_kb": "k", "target_id": "b", "target_kb": "k"},
            {"source_id": "b", "source_kb": "k", "target_id": "c", "target_kb": "k"},
            {"source_id": "c", "source_kb": "k", "target_id": "d", "target_kb": "k"},
            {"source_id": "d", "source_kb": "k", "target_id": "e", "target_kb": "k"},
        ]
        result = compute_betweenness_centrality(nodes, edges)
        # Middle node c should have the highest centrality
        assert result[("c", "k")] > result[("b", "k")]
        assert result[("c", "k")] > result[("d", "k")]
        # b and d should be symmetric
        assert abs(result[("b", "k")] - result[("d", "k")]) < 1e-10
        # Endpoints should have 0
        assert result[("a", "k")] == 0.0
        assert result[("e", "k")] == 0.0

    def test_cross_kb_edges(self):
        """Edges across KBs are handled correctly.

        Graph: (a,k1) - (b,k1) - (c,k2)
        b is on the path from a to c.
        """
        nodes = [
            {"id": "a", "kb_name": "k1"},
            {"id": "b", "kb_name": "k1"},
            {"id": "c", "kb_name": "k2"},
        ]
        edges = [
            {"source_id": "a", "source_kb": "k1", "target_id": "b", "target_kb": "k1"},
            {"source_id": "b", "source_kb": "k1", "target_id": "c", "target_kb": "k2"},
        ]
        result = compute_betweenness_centrality(nodes, edges)
        assert result[("b", "k1")] == 1.0
        assert result[("a", "k1")] == 0.0
        assert result[("c", "k2")] == 0.0

    def test_triangle_graph(self):
        """Triangle: all nodes have centrality 0 (no node is a bridge).

        Graph: a - b
               |   |
               +- c +
        """
        nodes = [
            {"id": "a", "kb_name": "k"},
            {"id": "b", "kb_name": "k"},
            {"id": "c", "kb_name": "k"},
        ]
        edges = [
            {"source_id": "a", "source_kb": "k", "target_id": "b", "target_kb": "k"},
            {"source_id": "b", "source_kb": "k", "target_id": "c", "target_kb": "k"},
            {"source_id": "a", "source_kb": "k", "target_id": "c", "target_kb": "k"},
        ]
        result = compute_betweenness_centrality(nodes, edges)
        assert result[("a", "k")] == 0.0
        assert result[("b", "k")] == 0.0
        assert result[("c", "k")] == 0.0


# =============================================================================
# API integration tests
# =============================================================================


@pytest.fixture
def graph_env():
    """Create test environment with linked entries for graph centrality tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"

        notes_path = tmpdir / "notes"
        notes_path.mkdir()

        notes_kb = KBConfig(
            name="test-notes",
            path=notes_path,
            kb_type=KBType.GENERIC,
        )

        config = PyriteConfig(
            knowledge_bases=[notes_kb], settings=Settings(index_path=db_path)
        )

        # Create entries that form a star: center -> leaf1, center -> leaf2, center -> leaf3
        repo = KBRepository(notes_kb)

        center = NoteEntry(id="center", title="Center Node", body="Hub of the star.")
        center.add_link("leaf1", relation="related_to", kb="test-notes")
        center.add_link("leaf2", relation="related_to", kb="test-notes")
        center.add_link("leaf3", relation="related_to", kb="test-notes")
        repo.save(center)

        for i in range(1, 4):
            leaf = NoteEntry(id=f"leaf{i}", title=f"Leaf {i}", body=f"Leaf node {i}.")
            repo.save(leaf)

        db = PyriteDB(db_path)
        index_mgr = IndexManager(db, config)
        index_mgr.index_all()

        import pyrite.server.api as api_module

        api_module._config = config
        api_module._db = db
        api_module._index_mgr = index_mgr

        app = create_app(config)
        client = TestClient(app)

        yield {
            "client": client,
            "config": config,
            "db": db,
            "notes_kb": notes_kb,
        }

        db.close()

        api_module._config = None
        api_module._db = None
        api_module._index_mgr = None


class TestGraphCentralityEndpoint:
    """Test the graph API endpoint with centrality."""

    def test_graph_without_centrality(self, graph_env):
        """Default request does not include centrality scores."""
        client = graph_env["client"]
        response = client.get("/api/graph")
        assert response.status_code == 200
        data = response.json()
        # All nodes should have centrality = 0.0 (default)
        for node in data["nodes"]:
            assert node["centrality"] == 0.0

    def test_graph_with_centrality(self, graph_env):
        """Request with include_centrality=true returns computed centrality."""
        client = graph_env["client"]
        response = client.get("/api/graph?include_centrality=true")
        assert response.status_code == 200
        data = response.json()

        assert len(data["nodes"]) >= 2  # At least some linked nodes

        # Find centrality values
        centralities = {n["id"]: n["centrality"] for n in data["nodes"]}

        # If the center node is present, it should have the highest centrality
        if "center" in centralities:
            center_c = centralities["center"]
            for nid, c in centralities.items():
                if nid != "center":
                    assert center_c >= c, f"Center ({center_c}) should be >= {nid} ({c})"

    def test_centrality_values_are_floats(self, graph_env):
        """Centrality values should be floats between 0 and 1."""
        client = graph_env["client"]
        response = client.get("/api/graph?include_centrality=true")
        assert response.status_code == 200
        data = response.json()
        for node in data["nodes"]:
            assert isinstance(node["centrality"], float)
            assert 0.0 <= node["centrality"] <= 1.0
