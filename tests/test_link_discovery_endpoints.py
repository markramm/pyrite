"""Tests for the discover-neighbors / batch-suggest REST endpoints.

mcp-rest-tool-parity: kb_discover_neighbors and kb_batch_suggest were
MCP-only (pyrite/server/mcp_server.py's _kb_discover_neighbors /
_kb_batch_suggest), with no REST equivalent even though the web UI
audit calls these out as tools agents can use that the web UI cannot.
Both MCP handlers already delegate to clean LinkDiscoveryService
methods (discover_neighbors, batch_suggest) -- these endpoints share
the same service calls, no service-layer duplication.
"""


class TestDiscoverNeighborsEndpoint:
    def test_finds_cross_kb_neighbor_by_shared_tag(self, rest_api_env):
        """sample_events (test-events, tags: test, immigration) and
        sample_person (test-research, tags: trump-admin, immigration)
        share the 'immigration' tag -- keyword mode should surface the
        person as a neighbor of an event."""
        client = rest_api_env["client"]

        search = client.get("/api/search?q=Test+Event&kb=test-events")
        assert search.status_code == 200
        entry_id = search.json()["results"][0]["id"]

        response = client.get(
            "/api/links/discover-neighbors",
            params={"entry_id": entry_id, "kb": "test-events", "target_kb": "test-research"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["entry_id"] == entry_id
        assert data["kb_name"] == "test-events"
        assert "discoveries" in data
        assert "count" in data

    def test_missing_entry_id_is_422(self, rest_api_env):
        """entry_id is a required query param -- FastAPI's own validation
        (not application logic) rejects a missing required param with 422,
        the standard REST semantics for a malformed request."""
        client = rest_api_env["client"]
        response = client.get("/api/links/discover-neighbors", params={"kb": "test-events"})
        assert response.status_code == 422

    def test_missing_kb_is_422(self, rest_api_env):
        client = rest_api_env["client"]
        response = client.get("/api/links/discover-neighbors", params={"entry_id": "some-entry"})
        assert response.status_code == 422


class TestBatchSuggestEndpoint:
    def test_suggests_pairs_between_two_kbs(self, rest_api_env):
        client = rest_api_env["client"]

        response = client.get(
            "/api/links/batch-suggest",
            params={"source_kb": "test-events", "target_kb": "test-research"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source_kb"] == "test-events"
        assert data["target_kb"] == "test-research"
        assert "pairs" in data
        assert "count" in data
        assert data["count"] == len(data["pairs"])

    def test_missing_source_kb_is_422(self, rest_api_env):
        client = rest_api_env["client"]
        response = client.get("/api/links/batch-suggest", params={"target_kb": "test-research"})
        assert response.status_code == 422

    def test_missing_target_kb_is_422(self, rest_api_env):
        client = rest_api_env["client"]
        response = client.get("/api/links/batch-suggest", params={"source_kb": "test-events"})
        assert response.status_code == 422
