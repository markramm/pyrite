"""
Tests for MCP Server.
"""

import json
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import EventEntry, PersonEntry
from pyrite.server.mcp_server import PyriteMCPServer
from pyrite.storage.repository import KBRepository


class TestPyriteMCPServer:
    """Tests for PyriteMCPServer."""

    @pytest.fixture
    def server_setup(self):
        """Create a test server with sample data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create DB
            db_path = tmpdir / "index.db"

            # Create KB directories
            events_path = tmpdir / "events"
            events_path.mkdir()

            research_path = tmpdir / "research"
            research_path.mkdir()
            (research_path / "actors").mkdir()

            # Create KB configs
            events_kb = KBConfig(
                name="test-events",
                path=events_path,
                kb_type=KBType.EVENTS,
                description="Test events KB",
            )

            research_kb = KBConfig(
                name="test-research",
                path=research_path,
                kb_type=KBType.RESEARCH,
                description="Test research KB",
            )

            config = PyriteConfig(
                knowledge_bases=[events_kb, research_kb], settings=Settings(index_path=db_path)
            )

            # Create some test entries
            events_repo = KBRepository(events_kb)
            for i in range(3):
                event = EventEntry.create(
                    date=f"2025-01-{10+i:02d}",
                    title=f"Test Event {i}",
                    body=f"This is test event {i} about immigration policy.",
                    importance=5 + i,
                )
                event.tags = ["test", "immigration"]
                event.actors = ["Stephen Miller", "Joe Biden"]
                events_repo.save(event)

            research_repo = KBRepository(research_kb)
            actor = PersonEntry.create(
                name="Stephen Miller", role="Immigration policy architect", importance=9
            )
            actor.body = "Stephen Miller is the architect of Trump's immigration policy."
            actor.tags = ["trump-admin", "immigration"]
            research_repo.save(actor)

            # Create server with admin tier (tests need create/update/delete/sync)
            server = PyriteMCPServer(config, tier="admin")

            # Index entries
            server.index_mgr.index_all()

            yield {
                "server": server,
                "config": config,
                "events_kb": events_kb,
                "research_kb": research_kb,
            }

            server.close()

    def test_kb_list(self, server_setup):
        """Test listing knowledge bases."""
        result = server_setup["server"].call_tool("kb_list", {})

        assert "knowledge_bases" in result
        kbs = result["knowledge_bases"]
        assert len(kbs) == 2

        kb_names = [kb["name"] for kb in kbs]
        assert "test-events" in kb_names
        assert "test-research" in kb_names

    def test_kb_search(self, server_setup):
        """Test full-text search."""
        result = server_setup["server"].call_tool("kb_search", {"query": "immigration"})

        assert "results" in result
        assert result["count"] >= 1

    def test_kb_search_with_filters(self, server_setup):
        """Test search with filters."""
        result = server_setup["server"].call_tool(
            "kb_search", {"query": "immigration", "kb_name": "test-events", "entry_type": "event"}
        )

        assert "results" in result
        for r in result["results"]:
            assert r["kb_name"] == "test-events"
            assert r["entry_type"] == "event"

    def test_kb_get(self, server_setup):
        """Test getting entry by ID."""
        # First search to get an ID
        search_result = server_setup["server"].call_tool(
            "kb_search", {"query": "Stephen Miller", "kb_name": "test-research"}
        )

        if search_result["count"] > 0:
            entry_id = search_result["results"][0]["id"]

            result = server_setup["server"].call_tool(
                "kb_get", {"entry_id": entry_id, "kb_name": "test-research"}
            )

            assert "entry" in result
            assert result["entry"]["title"] == "Stephen Miller"

    def test_kb_get_not_found(self, server_setup):
        """Test getting non-existent entry."""
        result = server_setup["server"].call_tool(
            "kb_get", {"entry_id": "nonexistent-entry", "kb_name": "test-events"}
        )

        assert "error" in result

    def test_kb_timeline(self, server_setup):
        """Test timeline queries."""
        result = server_setup["server"].call_tool(
            "kb_timeline", {"date_from": "2025-01-01", "date_to": "2025-01-31"}
        )

        assert "events" in result
        assert result["count"] >= 1

    def test_kb_timeline_with_importance(self, server_setup):
        """Test timeline with importance filter."""
        result = server_setup["server"].call_tool("kb_timeline", {"min_importance": 6})

        assert "events" in result
        for event in result["events"]:
            assert event.get("importance", 0) >= 6

    def test_kb_tags(self, server_setup):
        """Test getting all tags."""
        result = server_setup["server"].call_tool("kb_tags", {})

        assert "tags" in result
        tag_names = [t["tag"] for t in result["tags"]]
        assert "immigration" in tag_names

    def test_kb_create_event(self, server_setup):
        """Test creating a new event."""
        result = server_setup["server"].call_tool(
            "kb_create",
            {
                "kb_name": "test-events",
                "entry_type": "event",
                "title": "New Test Event",
                "body": "This is a newly created event.",
                "date": "2025-01-25",
                "importance": 7,
                "tags": ["new", "test"],
                "actors": ["Test Actor"],
            },
        )

        assert result.get("created") is True
        assert "entry_id" in result

        # Verify it can be retrieved
        get_result = server_setup["server"].call_tool(
            "kb_get", {"entry_id": result["entry_id"], "kb_name": "test-events"}
        )
        assert "entry" in get_result
        assert get_result["entry"]["title"] == "New Test Event"

    def test_kb_create_person(self, server_setup):
        """Test creating a new person entry."""
        result = server_setup["server"].call_tool(
            "kb_create",
            {
                "kb_name": "test-research",
                "entry_type": "person",
                "title": "New Test Actor",
                "body": "Biography of the test actor.",
                "role": "Test role",
                "importance": 5,
                "tags": ["new-actor"],
            },
        )

        assert result.get("created") is True
        assert "entry_id" in result

    def test_kb_update(self, server_setup):
        """Test updating an entry."""
        # Create an entry first
        create_result = server_setup["server"].call_tool(
            "kb_create",
            {
                "kb_name": "test-events",
                "entry_type": "event",
                "title": "Update Test Event",
                "date": "2025-01-26",
                "body": "Original body.",
            },
        )

        entry_id = create_result["entry_id"]

        # Update it
        update_result = server_setup["server"].call_tool(
            "kb_update",
            {
                "entry_id": entry_id,
                "kb_name": "test-events",
                "body": "Updated body content.",
                "importance": 8,
            },
        )

        assert update_result.get("updated") is True

        # Verify update
        get_result = server_setup["server"].call_tool(
            "kb_get", {"entry_id": entry_id, "kb_name": "test-events"}
        )
        assert "Updated body" in get_result["entry"]["body"]
        assert get_result["entry"]["importance"] == 8

    def test_kb_index_sync(self, server_setup):
        """Test index sync."""
        result = server_setup["server"].call_tool("kb_index_sync", {})

        assert result.get("synced") is True
        assert "added" in result
        assert "updated" in result
        assert "removed" in result


class TestMCPProtocol:
    """Test MCP protocol message handling."""

    @pytest.fixture
    def server(self):
        """Create a minimal server for protocol tests."""
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

    def test_initialize(self, server):
        """Test initialize message."""
        response = server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )

        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["serverInfo"]["name"].startswith("pyrite")

    def test_tools_list(self, server):
        """Test tools/list message."""
        response = server.handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )

        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]

        tool_names = [t["name"] for t in response["result"]["tools"]]
        assert "kb_list" in tool_names
        assert "kb_search" in tool_names
        assert "kb_get" in tool_names

    def test_tools_call(self, server):
        """Test tools/call message."""
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "kb_list", "arguments": {}},
            }
        )

        assert response["id"] == 3
        assert "result" in response
        assert "content" in response["result"]
        assert response["result"]["content"][0]["type"] == "text"

        # Parse the JSON content
        content = json.loads(response["result"]["content"][0]["text"])
        assert "knowledge_bases" in content

    def test_unknown_method(self, server):
        """Test unknown method returns error."""
        response = server.handle_message(
            {"jsonrpc": "2.0", "id": 4, "method": "unknown/method", "params": {}}
        )

        assert response["id"] == 4
        assert "error" in response
        assert response["error"]["code"] == -32601


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
