"""Tests for pyrite.formats — format registry, content negotiation, and serializers."""

import json

import pytest

# =============================================================================
# Format Registry
# =============================================================================


class TestFormatRegistry:
    def test_registry_has_four_defaults(self):
        from pyrite.formats import get_format_registry

        registry = get_format_registry()
        assert set(registry.available_formats()) == {"json", "markdown", "csv", "yaml"}

    def test_get_by_media_type_json(self):
        from pyrite.formats import get_format_registry

        registry = get_format_registry()
        spec = registry.get_by_media_type("application/json")
        assert spec is not None
        assert spec.name == "json"

    def test_get_by_media_type_markdown(self):
        from pyrite.formats import get_format_registry

        registry = get_format_registry()
        spec = registry.get_by_media_type("text/markdown")
        assert spec is not None
        assert spec.name == "markdown"

    def test_get_by_media_type_csv(self):
        from pyrite.formats import get_format_registry

        registry = get_format_registry()
        spec = registry.get_by_media_type("text/csv")
        assert spec is not None
        assert spec.name == "csv"

    def test_get_by_media_type_yaml(self):
        from pyrite.formats import get_format_registry

        registry = get_format_registry()
        spec = registry.get_by_media_type("text/yaml")
        assert spec is not None
        assert spec.name == "yaml"

    def test_get_by_media_type_unknown(self):
        from pyrite.formats import get_format_registry

        registry = get_format_registry()
        spec = registry.get_by_media_type("text/html")
        assert spec is None

    def test_get_by_name(self):
        from pyrite.formats import get_format_registry

        registry = get_format_registry()
        spec = registry.get("json")
        assert spec is not None
        assert spec.media_type == "application/json"
        assert spec.file_extension == "json"

    def test_get_by_name_unknown(self):
        from pyrite.formats import get_format_registry

        registry = get_format_registry()
        assert registry.get("xml") is None


# =============================================================================
# Content Negotiation
# =============================================================================


class TestNegotiateFormat:
    def test_empty_accept_returns_json(self):
        from pyrite.formats import negotiate_format

        assert negotiate_format("") == "json"

    def test_none_accept_returns_json(self):
        from pyrite.formats import negotiate_format

        assert negotiate_format(None) == "json"

    def test_wildcard_returns_json(self):
        from pyrite.formats import negotiate_format

        assert negotiate_format("*/*") == "json"

    def test_application_json(self):
        from pyrite.formats import negotiate_format

        assert negotiate_format("application/json") == "json"

    def test_text_markdown(self):
        from pyrite.formats import negotiate_format

        assert negotiate_format("text/markdown") == "markdown"

    def test_text_csv(self):
        from pyrite.formats import negotiate_format

        assert negotiate_format("text/csv") == "csv"

    def test_text_yaml(self):
        from pyrite.formats import negotiate_format

        assert negotiate_format("text/yaml") == "yaml"

    def test_unsupported_returns_none(self):
        from pyrite.formats import negotiate_format

        assert negotiate_format("text/html") is None

    def test_quality_factors(self):
        from pyrite.formats import negotiate_format

        result = negotiate_format("text/markdown, application/json;q=0.9")
        assert result == "markdown"

    def test_quality_factors_prefers_highest(self):
        from pyrite.formats import negotiate_format

        result = negotiate_format("text/markdown;q=0.5, application/json;q=0.9")
        assert result == "json"

    def test_wildcard_fallback_with_quality(self):
        from pyrite.formats import negotiate_format

        result = negotiate_format("text/html, */*;q=0.1")
        assert result == "json"


# =============================================================================
# format_response
# =============================================================================


class TestFormatResponse:
    def test_unknown_format_raises(self):
        from pyrite.formats import format_response

        with pytest.raises(ValueError, match="Unknown format"):
            format_response({"x": 1}, "xml")

    def test_returns_content_and_media_type(self):
        from pyrite.formats import format_response

        content, media_type = format_response({"x": 1}, "json")
        assert media_type == "application/json"
        assert '"x": 1' in content


# =============================================================================
# JSON Serializer
# =============================================================================


class TestJsonSerializer:
    def test_serialize_dict(self):
        from pyrite.formats.json_fmt import json_serialize

        result = json_serialize({"name": "test", "count": 42})
        parsed = json.loads(result)
        assert parsed == {"name": "test", "count": 42}

    def test_handles_dates(self):
        from datetime import date

        from pyrite.formats.json_fmt import json_serialize

        result = json_serialize({"date": date(2025, 1, 15)})
        parsed = json.loads(result)
        assert parsed["date"] == "2025-01-15"


# =============================================================================
# Markdown Serializer
# =============================================================================


class TestMarkdownSerializer:
    def test_entry_to_markdown(self):
        from pyrite.formats.markdown_fmt import markdown_serialize

        entry = {
            "id": "test-entry",
            "title": "Test Entry",
            "type": "note",
            "kb_name": "mydb",
            "body": "This is the body.",
        }
        result = markdown_serialize(entry)
        assert "---" in result
        assert "id: test-entry" in result
        assert "title: Test Entry" in result
        assert "This is the body." in result

    def test_entry_with_tags(self):
        from pyrite.formats.markdown_fmt import markdown_serialize

        entry = {
            "id": "test",
            "title": "Test",
            "tags": ["alpha", "beta"],
        }
        result = markdown_serialize(entry)
        assert "tags: [alpha, beta]" in result

    def test_entry_list(self):
        from pyrite.formats.markdown_fmt import markdown_serialize

        data = {
            "entries": [
                {"title": "First", "date": "2025-01-01", "tags": ["tag1"]},
                {"title": "Second"},
            ],
            "total": 2,
        }
        result = markdown_serialize(data)
        assert "# Entries (2 total)" in result
        assert "## First" in result
        assert "## Second" in result

    def test_search_results(self):
        from pyrite.formats.markdown_fmt import markdown_serialize

        data = {
            "query": "test",
            "count": 1,
            "results": [
                {"title": "Result One", "kb_name": "mydb", "snippet": "Some snippet text"},
            ],
        }
        result = markdown_serialize(data)
        assert "# Search: test (1 results)" in result
        assert "**Result One**" in result
        assert "Some snippet text" in result

    def test_tags(self):
        from pyrite.formats.markdown_fmt import markdown_serialize

        data = {"tags": [{"name": "alpha", "count": 5}, {"name": "beta", "count": 3}]}
        result = markdown_serialize(data)
        assert "# Tags (2 tags)" in result
        assert "alpha (5)" in result
        assert "beta (3)" in result

    def test_timeline(self):
        from pyrite.formats.markdown_fmt import markdown_serialize

        data = {
            "count": 1,
            "events": [{"date": "2025-01-01", "title": "Event One"}],
        }
        result = markdown_serialize(data)
        assert "# Timeline (1 events)" in result
        assert "**2025-01-01**" in result

    def test_kbs(self):
        from pyrite.formats.markdown_fmt import markdown_serialize

        data = {"kbs": [{"name": "mydb", "type": "research", "entries": 42}]}
        result = markdown_serialize(data)
        assert "# Knowledge Bases" in result
        assert "**mydb**" in result

    def test_fallback_to_str(self):
        from pyrite.formats.markdown_fmt import markdown_serialize

        result = markdown_serialize("just a string")
        assert result == "just a string"


# =============================================================================
# CSV Serializer
# =============================================================================


class TestCsvSerializer:
    def test_search_results_headers(self):
        from pyrite.formats.csv_fmt import csv_serialize

        data = {
            "results": [
                {"id": "e1", "kb_name": "kb1", "entry_type": "note", "title": "Title 1"},
            ]
        }
        result = csv_serialize(data)
        lines = result.strip().split("\n")
        assert "id" in lines[0]
        assert "title" in lines[0]
        assert "snippet" in lines[0]

    def test_tags_csv(self):
        from pyrite.formats.csv_fmt import csv_serialize

        data = {"tags": [{"name": "alpha", "count": 5}]}
        result = csv_serialize(data)
        lines = [line.strip() for line in result.strip().split("\n")]
        assert "tag,count" == lines[0]
        assert "alpha,5" == lines[1]

    def test_empty_results(self):
        from pyrite.formats.csv_fmt import csv_serialize

        data = {"results": []}
        result = csv_serialize(data)
        assert result == ""

    def test_entries_csv(self):
        from pyrite.formats.csv_fmt import csv_serialize

        data = {
            "entries": [
                {"id": "e1", "kb_name": "kb1", "entry_type": "note", "title": "T1"},
            ]
        }
        result = csv_serialize(data)
        assert "id,kb_name,entry_type,title" in result

    def test_events_csv(self):
        from pyrite.formats.csv_fmt import csv_serialize

        data = {
            "events": [
                {"id": "e1", "date": "2025-01-01", "title": "Event", "importance": 5},
            ]
        }
        result = csv_serialize(data)
        assert "id,date,title,importance" in result

    def test_kbs_csv(self):
        from pyrite.formats.csv_fmt import csv_serialize

        data = {"kbs": [{"name": "kb1", "type": "research", "path": "/tmp", "entries": 10}]}
        result = csv_serialize(data)
        assert "name,type,path,entries" in result

    def test_fallback_dict(self):
        from pyrite.formats.csv_fmt import csv_serialize

        data = {"foo": "bar", "num": 42}
        result = csv_serialize(data)
        assert "foo" in result
        assert "bar" in result


# =============================================================================
# YAML Serializer
# =============================================================================


class TestYamlSerializer:
    def test_dict_to_yaml(self):
        from pyrite.formats.yaml_fmt import yaml_serialize

        result = yaml_serialize({"name": "test", "count": 42})
        assert "name: test" in result
        assert "count: 42" in result

    def test_non_dict_fallback(self):
        from pyrite.formats.yaml_fmt import yaml_serialize

        result = yaml_serialize("just a string")
        assert result == "just a string"


# =============================================================================
# API Content Negotiation Integration
# =============================================================================


@pytest.fixture
def rest_api_env(indexed_test_env):
    """Test environment for REST API tests with TestClient."""
    from starlette.testclient import TestClient

    import pyrite.server.api as api_module
    from pyrite.server.api import create_app

    config = indexed_test_env["config"]
    db = indexed_test_env["db"]
    index_mgr = indexed_test_env["index_mgr"]

    api_module._config = config
    api_module._db = db
    api_module._index_mgr = index_mgr
    api_module._kb_service = None

    app = create_app(config)
    client = TestClient(app)

    yield {
        "client": client,
        "config": config,
        "db": db,
        "events_kb": indexed_test_env["events_kb"],
        "research_kb": indexed_test_env["research_kb"],
    }

    api_module._config = None
    api_module._db = None
    api_module._index_mgr = None
    api_module._kb_service = None


class TestApiContentNegotiation:
    def test_default_returns_json(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/kbs")
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]

    def test_accept_markdown_on_kbs(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/kbs", headers={"Accept": "text/markdown"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/markdown")
        assert "# Knowledge Bases" in resp.text

    def test_accept_csv_on_tags(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/tags", headers={"Accept": "text/csv"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "tag,count" in resp.text

    def test_accept_yaml_on_kbs(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/kbs", headers={"Accept": "text/yaml"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/yaml")

    def test_unsupported_accept_returns_406(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/kbs", headers={"Accept": "text/html"})
        assert resp.status_code == 406
        data = resp.json()
        assert data["error"] == "Not Acceptable"
        assert "supported_formats" in data

    def test_accept_markdown_on_entries(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/entries", headers={"Accept": "text/markdown"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/markdown")
        assert "# Entries" in resp.text

    def test_accept_csv_on_timeline(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/timeline", headers={"Accept": "text/csv"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")

    def test_json_accept_returns_normal_json(self, rest_api_env):
        """application/json in Accept should return normal Pydantic JSON."""
        client = rest_api_env["client"]
        resp = client.get("/api/kbs", headers={"Accept": "application/json"})
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
        data = resp.json()
        assert "kbs" in data

    def test_wildcard_accept_returns_json(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/kbs", headers={"Accept": "*/*"})
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
