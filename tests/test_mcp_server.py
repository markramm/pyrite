"""
Tests for MCP Server.
"""

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import EventEntry, NoteEntry, PersonEntry
from pyrite.schema import Link
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
        result = server_setup["server"]._dispatch_tool("kb_list", {})

        assert "knowledge_bases" in result
        kbs = result["knowledge_bases"]
        assert len(kbs) == 2

        kb_names = [kb["name"] for kb in kbs]
        assert "test-events" in kb_names
        assert "test-research" in kb_names

    def test_kb_search(self, server_setup):
        """Test full-text search."""
        result = server_setup["server"]._dispatch_tool("kb_search", {"query": "immigration"})

        assert "results" in result
        assert result["count"] >= 1

    def test_kb_search_with_filters(self, server_setup):
        """Test search with filters."""
        result = server_setup["server"]._dispatch_tool(
            "kb_search", {"query": "immigration", "kb_name": "test-events", "entry_type": "event"}
        )

        assert "results" in result
        for r in result["results"]:
            assert r["kb_name"] == "test-events"
            assert r["entry_type"] == "event"

    def test_kb_get(self, server_setup):
        """Test getting entry by ID."""
        # First search to get an ID
        search_result = server_setup["server"]._dispatch_tool(
            "kb_search", {"query": "Stephen Miller", "kb_name": "test-research"}
        )

        if search_result["count"] > 0:
            entry_id = search_result["results"][0]["id"]

            result = server_setup["server"]._dispatch_tool(
                "kb_get", {"entry_id": entry_id, "kb_name": "test-research"}
            )

            assert "entry" in result
            assert result["entry"]["title"] == "Stephen Miller"

    def test_kb_get_not_found(self, server_setup):
        """Test getting non-existent entry."""
        result = server_setup["server"]._dispatch_tool(
            "kb_get", {"entry_id": "nonexistent-entry", "kb_name": "test-events"}
        )

        assert "error" in result

    def test_kb_timeline(self, server_setup):
        """Test timeline queries."""
        result = server_setup["server"]._dispatch_tool(
            "kb_timeline", {"date_from": "2025-01-01", "date_to": "2025-01-31"}
        )

        assert "events" in result
        assert result["count"] >= 1

    def test_kb_timeline_with_importance(self, server_setup):
        """Test timeline with importance filter."""
        result = server_setup["server"]._dispatch_tool("kb_timeline", {"min_importance": 6})

        assert "events" in result
        for event in result["events"]:
            assert event.get("importance", 0) >= 6

    def test_kb_tags(self, server_setup):
        """Test getting all tags."""
        result = server_setup["server"]._dispatch_tool("kb_tags", {})

        assert "tags" in result
        tag_names = [t["tag"] for t in result["tags"]]
        assert "immigration" in tag_names

    def test_kb_create_event(self, server_setup):
        """Test creating a new event."""
        result = server_setup["server"]._dispatch_tool(
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
        get_result = server_setup["server"]._dispatch_tool(
            "kb_get", {"entry_id": result["entry_id"], "kb_name": "test-events"}
        )
        assert "entry" in get_result
        assert get_result["entry"]["title"] == "New Test Event"

    def test_kb_create_person(self, server_setup):
        """Test creating a new person entry."""
        result = server_setup["server"]._dispatch_tool(
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
        create_result = server_setup["server"]._dispatch_tool(
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
        update_result = server_setup["server"]._dispatch_tool(
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
        get_result = server_setup["server"]._dispatch_tool(
            "kb_get", {"entry_id": entry_id, "kb_name": "test-events"}
        )
        assert "Updated body" in get_result["entry"]["body"]
        assert get_result["entry"]["importance"] == 8

    def test_kb_index_sync(self, server_setup):
        """Test index sync."""
        result = server_setup["server"]._dispatch_tool("kb_index_sync", {})

        assert result.get("synced") is True
        assert "added" in result
        assert "updated" in result
        assert "removed" in result

    # ------------------------------------------------------------------
    # Delete handler
    # ------------------------------------------------------------------

    def test_kb_delete(self, server_setup):
        """Test deleting an entry removes it from the KB."""
        server = server_setup["server"]

        # Create an entry to delete
        create_result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "test-events",
                "entry_type": "event",
                "title": "Ephemeral Event",
                "date": "2025-02-01",
                "body": "This will be deleted.",
            },
        )
        assert create_result.get("created") is True
        entry_id = create_result["entry_id"]

        # Delete it
        delete_result = server._dispatch_tool(
            "kb_delete", {"entry_id": entry_id, "kb_name": "test-events"}
        )
        assert delete_result.get("deleted") is True
        assert delete_result["entry_id"] == entry_id

        # Verify it's gone
        get_result = server._dispatch_tool(
            "kb_get", {"entry_id": entry_id, "kb_name": "test-events"}
        )
        assert "error" in get_result

    def test_kb_delete_not_found(self, server_setup):
        """Test deleting a non-existent entry returns an error."""
        result = server_setup["server"]._dispatch_tool(
            "kb_delete", {"entry_id": "no-such-entry", "kb_name": "test-events"}
        )
        assert "error" in result

    # ------------------------------------------------------------------
    # Backlinks handler
    # ------------------------------------------------------------------

    def test_kb_backlinks(self, server_setup):
        """Test backlinks returns entries that link TO a given entry."""
        server = server_setup["server"]
        events_kb = server_setup["events_kb"]
        repo = KBRepository(events_kb)

        # Create target entry
        target = EventEntry.create(
            date="2025-03-01", title="Target Event", body="Target.", importance=5
        )
        repo.save(target)

        # Create source entry that links to target
        source = EventEntry.create(
            date="2025-03-02", title="Source Event", body="Links to target.", importance=5
        )
        source.links = [Link(target=target.id, relation="related_to")]
        repo.save(source)

        # Re-index to pick up links
        server.index_mgr.index_all()

        result = server._dispatch_tool(
            "kb_backlinks", {"entry_id": target.id, "kb_name": "test-events"}
        )

        assert result["entry_id"] == target.id
        assert result["backlink_count"] >= 1
        backlink_ids = [bl["id"] for bl in result["backlinks"]]
        assert source.id in backlink_ids

    # ------------------------------------------------------------------
    # Stats handler
    # ------------------------------------------------------------------

    def test_kb_stats(self, server_setup):
        """Test stats returns entry/tag/link counts."""
        result = server_setup["server"]._dispatch_tool("kb_stats", {})

        assert "total_entries" in result
        assert result["total_entries"] >= 4  # 3 events + 1 person
        assert "total_tags" in result
        assert "total_links" in result
        assert "kbs" in result

    # ------------------------------------------------------------------
    # Schema handler
    # ------------------------------------------------------------------

    def test_kb_schema(self, server_setup):
        """Test schema returns type information for a KB."""
        result = server_setup["server"]._dispatch_tool(
            "kb_schema", {"kb_name": "test-events"}
        )

        # Schema may be empty (no kb.yaml in test tmpdir) but should not error
        assert "error" not in result

    def test_kb_schema_not_found(self, server_setup):
        """Test schema for a non-existent KB returns error."""
        result = server_setup["server"]._dispatch_tool(
            "kb_schema", {"kb_name": "nonexistent-kb"}
        )
        assert "error" in result

    # ------------------------------------------------------------------
    # Manage handler
    # ------------------------------------------------------------------

    def test_kb_manage_validate(self, server_setup):
        """Test manage validate action returns KB validation info."""
        result = server_setup["server"]._dispatch_tool(
            "kb_manage", {"action": "validate", "kb_name": "test-events"}
        )

        assert result.get("valid") is True
        assert "types" in result

    def test_kb_manage_validate_not_found(self, server_setup):
        """Test manage validate for non-existent KB returns error."""
        result = server_setup["server"]._dispatch_tool(
            "kb_manage", {"action": "validate", "kb_name": "nonexistent"}
        )
        assert "error" in result

    # ------------------------------------------------------------------
    # Metadata round-trip (regression for build_entry metadata bug)
    # ------------------------------------------------------------------

    def test_kb_create_with_metadata_generic_type(self, server_setup):
        """Test create with metadata dict round-trips for generic entry types."""
        server = server_setup["server"]

        # Use a generic type (not event/person/org) so metadata is stored
        create_result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "test-events",
                "entry_type": "note",
                "title": "Metadata Note",
                "body": "Has custom metadata.",
                "metadata": {"source_url": "https://example.com", "category": "test"},
            },
        )
        assert create_result.get("created") is True

        get_result = server._dispatch_tool(
            "kb_get", {"entry_id": create_result["entry_id"], "kb_name": "test-events"}
        )
        assert "entry" in get_result
        entry = get_result["entry"]
        # Metadata may be a JSON string or dict depending on DB layer
        import json as _json

        metadata = entry.get("metadata", {})
        if isinstance(metadata, str):
            metadata = _json.loads(metadata) if metadata else {}
        assert metadata.get("source_url") == "https://example.com"

    def test_kb_create_event_with_metadata(self, server_setup):
        """Test create event with metadata dict preserves custom fields."""
        server = server_setup["server"]

        create_result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "test-events",
                "entry_type": "event",
                "title": "Event With Metadata",
                "date": "2025-02-15",
                "body": "Event with custom metadata.",
                "metadata": {"source_url": "https://example.com/event", "custom_field": "value"},
            },
        )
        assert create_result.get("created") is True

        get_result = server._dispatch_tool(
            "kb_get", {"entry_id": create_result["entry_id"], "kb_name": "test-events"}
        )
        assert "entry" in get_result
        import json as _json

        metadata = get_result["entry"].get("metadata", {})
        if isinstance(metadata, str):
            metadata = _json.loads(metadata) if metadata else {}
        assert metadata.get("source_url") == "https://example.com/event"

    def test_kb_create_person_with_metadata(self, server_setup):
        """Test create person with metadata dict preserves custom fields."""
        server = server_setup["server"]

        create_result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "test-research",
                "entry_type": "person",
                "title": "Person With Metadata",
                "body": "A person with custom metadata.",
                "role": "Analyst",
                "metadata": {"linkedin": "https://linkedin.com/in/test"},
            },
        )
        assert create_result.get("created") is True

        get_result = server._dispatch_tool(
            "kb_get", {"entry_id": create_result["entry_id"], "kb_name": "test-research"}
        )
        assert "entry" in get_result
        import json as _json

        metadata = get_result["entry"].get("metadata", {})
        if isinstance(metadata, str):
            metadata = _json.loads(metadata) if metadata else {}
        assert metadata.get("linkedin") == "https://linkedin.com/in/test"

    def test_kb_create_with_empty_metadata(self, server_setup):
        """Test create with empty metadata dict doesn't cause errors."""
        server = server_setup["server"]

        result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "test-events",
                "entry_type": "event",
                "title": "Empty Metadata Event",
                "date": "2025-02-11",
                "body": "No custom metadata.",
                "metadata": {},
            },
        )
        assert result.get("created") is True

    # ------------------------------------------------------------------
    # Error handling on writes
    # ------------------------------------------------------------------

    def test_kb_create_readonly_kb(self):
        """Test creating on a read-only KB returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"
            ro_path = tmpdir / "readonly-kb"
            ro_path.mkdir()

            ro_kb = KBConfig(
                name="readonly",
                path=ro_path,
                kb_type=KBType.RESEARCH,
                read_only=True,
            )
            config = PyriteConfig(
                knowledge_bases=[ro_kb], settings=Settings(index_path=db_path)
            )
            server = PyriteMCPServer(config, tier="write")
            try:
                result = server._dispatch_tool(
                    "kb_create",
                    {
                        "kb_name": "readonly",
                        "entry_type": "note",
                        "title": "Should Fail",
                    },
                )
                assert "error" in result
                assert "read-only" in result["error"]
            finally:
                server.close()

    def test_kb_update_not_found(self, server_setup):
        """Test updating a non-existent entry returns error."""
        result = server_setup["server"]._dispatch_tool(
            "kb_update",
            {
                "entry_id": "no-such-entry",
                "kb_name": "test-events",
                "body": "Should fail.",
            },
        )
        assert "error" in result

    # ------------------------------------------------------------------
    # Search edge cases
    # ------------------------------------------------------------------

    def test_kb_search_boolean_operators(self, server_setup):
        """Test FTS5 boolean operators work in search."""
        result = server_setup["server"]._dispatch_tool(
            "kb_search", {"query": "immigration AND policy"}
        )

        assert "results" in result
        assert result["count"] >= 1

    def test_kb_search_no_results(self, server_setup):
        """Test search with no matches returns count=0."""
        result = server_setup["server"]._dispatch_tool(
            "kb_search", {"query": "xyzzy_nonexistent_term_12345"}
        )

        assert result["count"] == 0
        assert result["results"] == []


class TestMCPProtocol:
    """Test MCP server business methods (protocol dispatch handled by SDK)."""

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

    def test_get_tools_list(self, server):
        """Test get_tools_list returns tool definitions."""
        tools = server.get_tools_list()
        tool_names = [t["name"] for t in tools]
        assert "kb_list" in tool_names
        assert "kb_search" in tool_names
        assert "kb_get" in tool_names
        for t in tools:
            assert "name" in t
            assert "description" in t
            assert "inputSchema" in t

    def test_dispatch_tool(self, server):
        """Test _dispatch_tool calls handler and returns result."""
        result = server._dispatch_tool("kb_list", {})
        assert "knowledge_bases" in result

    def test_dispatch_tool_unknown(self, server):
        """Test _dispatch_tool returns error for unknown tool."""
        result = server._dispatch_tool("nonexistent_tool", {})
        assert "error" in result

    def test_build_sdk_server(self, server):
        """Test build_sdk_server returns a configured SDK Server."""
        from mcp.server import Server

        sdk = server.build_sdk_server()
        assert isinstance(sdk, Server)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
