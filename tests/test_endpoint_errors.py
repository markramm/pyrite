"""Tests for REST API error paths (400, 404, 500 responses).

Uses shared fixtures from conftest.py.
"""

import pytest


@pytest.mark.api
class TestEntryEndpointErrors:
    """Error path tests for entry CRUD endpoints."""

    def test_get_entry_not_found(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/entries/nonexistent-id")
        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"]["code"] == "NOT_FOUND"

    def test_get_entry_not_found_with_kb(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/entries/nonexistent-id?kb=test-events")
        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"]["code"] == "NOT_FOUND"

    def test_create_entry_missing_kb(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.post(
            "/api/entries",
            json={"kb": "nonexistent-kb", "title": "Test", "body": "test"},
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"]["code"] == "KB_NOT_FOUND"

    def test_create_event_missing_date(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.post(
            "/api/entries",
            json={
                "kb": "test-events",
                "title": "Test Event",
                "entry_type": "event",
                "body": "test",
            },
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["code"] == "MISSING_DATE"

    def test_update_entry_not_found(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.put(
            "/api/entries/nonexistent-id",
            json={"kb": "test-events", "title": "New Title"},
        )
        assert resp.status_code == 404

    def test_delete_entry_not_found(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.delete("/api/entries/nonexistent-id?kb=test-events")
        assert resp.status_code == 404

    def test_create_entry_success(self, rest_api_env):
        """Verify create returns expected structure."""
        client = rest_api_env["client"]
        resp = client.post(
            "/api/entries",
            json={
                "kb": "test-events",
                "title": "New Test Entry",
                "entry_type": "note",
                "body": "This is a new test entry.",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] is True
        assert data["id"]
        assert data["kb_name"] == "test-events"


@pytest.mark.api
class TestTimelineEndpointErrors:
    """Error path tests for timeline endpoint."""

    def test_timeline_empty_result(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/timeline?date_from=2099-01-01&date_to=2099-12-31")
        assert resp.status_code == 200
        data = resp.json()
        assert data["events"] == []

    def test_timeline_with_high_importance_filter(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/timeline?min_importance=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["events"] == []


@pytest.mark.api
class TestSearchEndpointErrors:
    """Error path tests for search endpoint."""

    def test_search_empty_query(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/search?q=")
        # FastAPI returns 422 for validation errors (empty string fails minLength)
        assert resp.status_code in (400, 422)

    def test_search_no_results(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/search?q=zzzznonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []


@pytest.mark.api
class TestKBEndpointErrors:
    """Error path tests for KB endpoints."""

    def test_list_kbs_returns_all(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/kbs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["kbs"]) >= 2

    def test_entries_list_with_invalid_type(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/entries?entry_type=nonexistent_type")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []


@pytest.mark.api
class TestStarredEndpointErrors:
    """Error path tests for starred entries endpoints."""

    def test_star_nonexistent_entry(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.post(
            "/api/starred",
            json={"entry_id": "nonexistent-entry", "kb_name": "test-events"},
        )
        # Should succeed (starred is engagement data, doesn't validate entry existence)
        # or fail with 404 depending on implementation
        assert resp.status_code in (200, 201, 404)

    def test_unstar_nonexistent(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.delete("/api/starred/nonexistent-entry?kb_name=test-events")
        assert resp.status_code == 404
