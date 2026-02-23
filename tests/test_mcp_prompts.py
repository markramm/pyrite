"""
Tests for MCP Prompts and Resources.
"""

import json
import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.server.mcp_server import PyriteMCPServer


@pytest.fixture
def mcp_server(indexed_test_env):
    """MCP server with indexed test data."""
    env = indexed_test_env
    server = PyriteMCPServer(config=env["config"], tier="read")
    yield server
    server.close()


@pytest.fixture
def mcp_server_minimal():
    """Minimal MCP server for protocol-level tests (no indexed data)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"
        kb_path = tmpdir / "kb"
        kb_path.mkdir()

        config = PyriteConfig(
            knowledge_bases=[KBConfig(name="test", path=kb_path, kb_type=KBType.EVENTS)],
            settings=Settings(index_path=db_path),
        )

        server = PyriteMCPServer(config)
        yield server
        server.close()


# =========================================================================
# Prompt Tests
# =========================================================================


class TestPromptsList:
    """Tests for prompts/list."""

    def test_prompts_list_returns_all_prompts(self, mcp_server):
        """prompts/list returns all 4 prompts."""
        response = mcp_server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": {}}
        )

        assert response["id"] == 1
        assert "result" in response
        prompts = response["result"]["prompts"]
        assert len(prompts) == 4

        names = {p["name"] for p in prompts}
        assert names == {"research_topic", "summarize_entry", "find_connections", "daily_briefing"}

    def test_each_prompt_has_required_fields(self, mcp_server):
        """Each prompt has name, description, and arguments."""
        response = mcp_server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": {}}
        )

        for prompt in response["result"]["prompts"]:
            assert "name" in prompt
            assert "description" in prompt
            assert "arguments" in prompt
            assert isinstance(prompt["arguments"], list)

    def test_prompt_arguments_have_required_fields(self, mcp_server):
        """Each argument has name, description, and required fields."""
        response = mcp_server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": {}}
        )

        for prompt in response["result"]["prompts"]:
            for arg in prompt["arguments"]:
                assert "name" in arg
                assert "description" in arg
                assert "required" in arg


class TestPromptsGet:
    """Tests for prompts/get."""

    def test_research_topic_returns_messages(self, mcp_server):
        """prompts/get for research_topic returns messages with the topic."""
        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "prompts/get",
                "params": {"name": "research_topic", "arguments": {"topic": "immigration"}},
            }
        )

        assert "result" in response
        messages = response["result"]["messages"]
        assert len(messages) >= 1
        assert messages[0]["role"] == "user"
        assert "immigration" in messages[0]["content"]["text"]

    def test_summarize_entry_with_valid_entry(self, mcp_server):
        """prompts/get for summarize_entry returns entry content."""
        # Get an entry ID from search
        search_resp = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "kb_search", "arguments": {"query": "Stephen Miller"}},
            }
        )
        search_data = json.loads(search_resp["result"]["content"][0]["text"])
        entry_id = search_data["results"][0]["id"]

        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "prompts/get",
                "params": {
                    "name": "summarize_entry",
                    "arguments": {"entry_id": entry_id, "kb_name": "test-research"},
                },
            }
        )

        assert "result" in response
        messages = response["result"]["messages"]
        assert len(messages) >= 1
        assert "Summarize" in messages[0]["content"]["text"]
        # Entry content should be included
        assert "Stephen Miller" in messages[0]["content"]["text"]

    def test_summarize_entry_with_invalid_entry(self, mcp_server):
        """prompts/get for summarize_entry handles missing entry gracefully."""
        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "prompts/get",
                "params": {
                    "name": "summarize_entry",
                    "arguments": {"entry_id": "nonexistent-entry"},
                },
            }
        )

        assert "result" in response
        messages = response["result"]["messages"]
        assert len(messages) >= 1
        # Should still return a message, not an error
        assert "not found" in messages[0]["content"]["text"].lower()

    def test_find_connections_returns_both_entries(self, mcp_server):
        """prompts/get for find_connections returns content about both entries."""
        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "prompts/get",
                "params": {
                    "name": "find_connections",
                    "arguments": {"entry_a": "some-entry-a", "entry_b": "some-entry-b"},
                },
            }
        )

        assert "result" in response
        messages = response["result"]["messages"]
        assert len(messages) >= 1
        text = messages[0]["content"]["text"]
        assert "Entry A" in text
        assert "Entry B" in text
        assert "connections" in text.lower()

    def test_daily_briefing_returns_recent_data(self, mcp_server):
        """prompts/get for daily_briefing returns briefing context."""
        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "prompts/get",
                "params": {"name": "daily_briefing", "arguments": {"days": "30"}},
            }
        )

        assert "result" in response
        messages = response["result"]["messages"]
        assert len(messages) >= 1
        text = messages[0]["content"]["text"]
        assert "briefing" in text.lower()

    def test_daily_briefing_default_days(self, mcp_server):
        """daily_briefing defaults to 7 days when not specified."""
        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "prompts/get",
                "params": {"name": "daily_briefing", "arguments": {}},
            }
        )

        assert "result" in response
        messages = response["result"]["messages"]
        assert "7 days" in messages[0]["content"]["text"]

    def test_unknown_prompt_returns_error(self, mcp_server):
        """prompts/get for unknown prompt returns error."""
        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "prompts/get",
                "params": {"name": "nonexistent_prompt", "arguments": {}},
            }
        )

        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "nonexistent_prompt" in response["error"]["message"]


# =========================================================================
# Resource Tests
# =========================================================================


class TestResourcesList:
    """Tests for resources/list."""

    def test_resources_list_returns_static_resources(self, mcp_server):
        """resources/list returns the static pyrite://kbs resource."""
        response = mcp_server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}}
        )

        assert "result" in response
        resources = response["result"]["resources"]
        assert len(resources) >= 1

        uris = {r["uri"] for r in resources}
        assert "pyrite://kbs" in uris

    def test_resources_have_required_fields(self, mcp_server):
        """Each resource has uri, name, description, mimeType."""
        response = mcp_server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}}
        )

        for resource in response["result"]["resources"]:
            assert "uri" in resource
            assert "name" in resource
            assert "description" in resource
            assert "mimeType" in resource


class TestResourceTemplatesList:
    """Tests for resources/templates/list."""

    def test_templates_list_returns_templates(self, mcp_server):
        """resources/templates/list returns URI templates."""
        response = mcp_server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "resources/templates/list", "params": {}}
        )

        assert "result" in response
        templates = response["result"]["resourceTemplates"]
        assert len(templates) == 2

        uri_templates = {t["uriTemplate"] for t in templates}
        assert "pyrite://kbs/{name}/entries" in uri_templates
        assert "pyrite://entries/{id}" in uri_templates

    def test_templates_have_required_fields(self, mcp_server):
        """Each template has uriTemplate, name, description, mimeType."""
        response = mcp_server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "resources/templates/list", "params": {}}
        )

        for template in response["result"]["resourceTemplates"]:
            assert "uriTemplate" in template
            assert "name" in template
            assert "description" in template
            assert "mimeType" in template


class TestResourcesRead:
    """Tests for resources/read."""

    def test_read_kbs_returns_kb_list(self, mcp_server):
        """resources/read for pyrite://kbs returns KB list."""
        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resources/read",
                "params": {"uri": "pyrite://kbs"},
            }
        )

        assert "result" in response
        contents = response["result"]["contents"]
        assert len(contents) == 1
        assert contents[0]["uri"] == "pyrite://kbs"
        assert contents[0]["mimeType"] == "application/json"

        data = json.loads(contents[0]["text"])
        assert isinstance(data, list)
        kb_names = [kb["name"] for kb in data]
        assert "test-events" in kb_names
        assert "test-research" in kb_names

    def test_read_kb_entries_returns_entries(self, mcp_server):
        """resources/read for pyrite://kbs/{name}/entries returns entry list."""
        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resources/read",
                "params": {"uri": "pyrite://kbs/test-events/entries"},
            }
        )

        assert "result" in response
        contents = response["result"]["contents"]
        assert len(contents) == 1
        assert contents[0]["uri"] == "pyrite://kbs/test-events/entries"
        assert contents[0]["mimeType"] == "application/json"

        data = json.loads(contents[0]["text"])
        assert isinstance(data, list)

    def test_read_entry_returns_entry(self, mcp_server):
        """resources/read for pyrite://entries/{id} returns entry data."""
        # First find an entry ID
        search_resp = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "kb_search", "arguments": {"query": "Stephen Miller"}},
            }
        )
        search_data = json.loads(search_resp["result"]["content"][0]["text"])
        entry_id = search_data["results"][0]["id"]

        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "resources/read",
                "params": {"uri": f"pyrite://entries/{entry_id}"},
            }
        )

        assert "result" in response
        contents = response["result"]["contents"]
        assert len(contents) == 1
        assert contents[0]["mimeType"] == "application/json"

        data = json.loads(contents[0]["text"])
        assert data["title"] == "Stephen Miller"

    def test_read_entry_not_found(self, mcp_server):
        """resources/read for nonexistent entry returns error."""
        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resources/read",
                "params": {"uri": "pyrite://entries/nonexistent-id"},
            }
        )

        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_read_unknown_uri_returns_error(self, mcp_server):
        """resources/read for unknown URI returns error."""
        response = mcp_server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resources/read",
                "params": {"uri": "pyrite://unknown/path"},
            }
        )

        assert "error" in response
        assert response["error"]["code"] == -32602


# =========================================================================
# Capability Advertisement Tests
# =========================================================================


class TestCapabilities:
    """Test that initialize advertises prompts and resources."""

    def test_initialize_advertises_prompts(self, mcp_server_minimal):
        """initialize response includes prompts capability."""
        response = mcp_server_minimal.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )

        capabilities = response["result"]["capabilities"]
        assert "prompts" in capabilities
        assert "resources" in capabilities
        assert "tools" in capabilities

    def test_prompts_available_at_all_tiers(self):
        """Prompts are available at read, write, and admin tiers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"
            kb_path = tmpdir / "kb"
            kb_path.mkdir()

            config = PyriteConfig(
                knowledge_bases=[KBConfig(name="test", path=kb_path, kb_type=KBType.EVENTS)],
                settings=Settings(index_path=db_path),
            )

            for tier in ("read", "write", "admin"):
                server = PyriteMCPServer(config, tier=tier)
                try:
                    assert len(server.prompts) == 4, f"Tier {tier} should have 4 prompts"
                    assert len(server.resources) >= 1, f"Tier {tier} should have resources"
                    assert (
                        len(server.resource_templates) == 2
                    ), f"Tier {tier} should have 2 templates"
                finally:
                    server.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
