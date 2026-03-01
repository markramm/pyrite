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

    # ------------------------------------------------------------------
    # kb_bulk_create handler
    # ------------------------------------------------------------------

    def test_kb_bulk_create(self, server_setup):
        """Test batch-creating multiple entries."""
        server = server_setup["server"]

        result = server._dispatch_tool(
            "kb_bulk_create",
            {
                "kb_name": "test-events",
                "entries": [
                    {
                        "entry_type": "event",
                        "title": "Bulk Event A",
                        "date": "2025-05-01",
                        "body": "First bulk event.",
                        "tags": ["bulk"],
                    },
                    {
                        "entry_type": "event",
                        "title": "Bulk Event B",
                        "date": "2025-05-02",
                        "body": "Second bulk event.",
                    },
                    {
                        "entry_type": "note",
                        "title": "Bulk Note C",
                        "body": "A note in the batch.",
                    },
                ],
            },
        )

        assert result["total"] == 3
        assert result["created"] == 3
        assert result["failed"] == 0
        for r in result["results"]:
            assert r["created"] is True
            assert "entry_id" in r

        # Verify entries are retrievable
        for r in result["results"]:
            get = server._dispatch_tool(
                "kb_get", {"entry_id": r["entry_id"], "kb_name": "test-events"}
            )
            assert "entry" in get

    def test_kb_bulk_create_partial_failure(self, server_setup):
        """Test bulk create with some entries failing."""
        server = server_setup["server"]

        result = server._dispatch_tool(
            "kb_bulk_create",
            {
                "kb_name": "test-events",
                "entries": [
                    {
                        "entry_type": "event",
                        "title": "Good Entry",
                        "date": "2025-05-10",
                        "body": "This should succeed.",
                    },
                    {
                        # Missing title — should fail
                        "entry_type": "event",
                        "body": "No title here.",
                    },
                ],
            },
        )

        assert result["total"] == 2
        assert result["created"] == 1
        assert result["failed"] == 1
        assert result["results"][0]["created"] is True
        assert result["results"][1]["created"] is False
        assert "title" in result["results"][1]["error"].lower()

    def test_kb_bulk_create_empty(self, server_setup):
        """Test bulk create with empty entries array."""
        result = server_setup["server"]._dispatch_tool(
            "kb_bulk_create",
            {"kb_name": "test-events", "entries": []},
        )
        assert "error" in result

    def test_kb_bulk_create_readonly(self):
        """Test bulk create on read-only KB returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            ro_path = tmpdir / "readonly-kb"
            ro_path.mkdir()

            config = PyriteConfig(
                knowledge_bases=[
                    KBConfig(name="ro", path=ro_path, kb_type=KBType.RESEARCH, read_only=True)
                ],
                settings=Settings(index_path=tmpdir / "index.db"),
            )
            server = PyriteMCPServer(config, tier="write")
            try:
                result = server._dispatch_tool(
                    "kb_bulk_create",
                    {
                        "kb_name": "ro",
                        "entries": [{"title": "Should Fail"}],
                    },
                )
                assert "error" in result
                assert "read-only" in result["error"]
            finally:
                server.close()

    def test_kb_bulk_create_over_limit(self, server_setup):
        """Test bulk create rejects more than 50 entries."""
        entries = [{"title": f"Entry {i}"} for i in range(51)]
        result = server_setup["server"]._dispatch_tool(
            "kb_bulk_create",
            {"kb_name": "test-events", "entries": entries},
        )
        assert "error" in result
        assert "50" in result["error"]

    # ------------------------------------------------------------------
    # kb_link handler
    # ------------------------------------------------------------------

    def test_kb_link(self, server_setup):
        """Test creating a link between two entries via kb_link."""
        server = server_setup["server"]

        # Create two entries
        r1 = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "test-events",
                "entry_type": "event",
                "title": "Link Source",
                "date": "2025-04-01",
                "body": "Source entry.",
            },
        )
        r2 = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "test-events",
                "entry_type": "event",
                "title": "Link Target",
                "date": "2025-04-02",
                "body": "Target entry.",
            },
        )
        assert r1.get("created") and r2.get("created")

        # Link them
        link_result = server._dispatch_tool(
            "kb_link",
            {
                "source_id": r1["entry_id"],
                "source_kb": "test-events",
                "target_id": r2["entry_id"],
                "relation": "caused_by",
            },
        )
        assert link_result.get("linked") is True
        assert link_result["relation"] == "caused_by"

        # Verify via backlinks
        bl = server._dispatch_tool(
            "kb_backlinks",
            {"entry_id": r2["entry_id"], "kb_name": "test-events"},
        )
        backlink_ids = [b["id"] for b in bl["backlinks"]]
        assert r1["entry_id"] in backlink_ids

    def test_kb_link_idempotent(self, server_setup):
        """Test linking the same pair twice doesn't create duplicate links."""
        server = server_setup["server"]

        r1 = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "test-events",
                "entry_type": "event",
                "title": "Idem Source",
                "date": "2025-04-03",
                "body": "Source.",
            },
        )
        r2 = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "test-events",
                "entry_type": "event",
                "title": "Idem Target",
                "date": "2025-04-04",
                "body": "Target.",
            },
        )

        args = {
            "source_id": r1["entry_id"],
            "source_kb": "test-events",
            "target_id": r2["entry_id"],
        }
        result1 = server._dispatch_tool("kb_link", args)
        result2 = server._dispatch_tool("kb_link", args)
        assert result1.get("linked") is True
        assert result2.get("linked") is True

        # Only one backlink should exist
        bl = server._dispatch_tool(
            "kb_backlinks",
            {"entry_id": r2["entry_id"], "kb_name": "test-events"},
        )
        source_links = [b for b in bl["backlinks"] if b["id"] == r1["entry_id"]]
        assert len(source_links) == 1

    def test_kb_link_not_found(self, server_setup):
        """Test linking from a nonexistent entry returns error."""
        result = server_setup["server"]._dispatch_tool(
            "kb_link",
            {
                "source_id": "no-such-entry",
                "source_kb": "test-events",
                "target_id": "also-missing",
            },
        )
        assert "error" in result

    def test_kb_link_in_write_tier(self):
        """Test kb_link appears in write-tier tools but not read-tier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"
            kb_path = tmpdir / "kb"
            kb_path.mkdir()

            config = PyriteConfig(
                knowledge_bases=[KBConfig(name="t", path=kb_path, kb_type=KBType.EVENTS)],
                settings=Settings(index_path=db_path),
            )

            read_server = PyriteMCPServer(config, tier="read")
            write_server = PyriteMCPServer(config, tier="write")

            read_names = [t["name"] for t in read_server.get_tools_list()]
            write_names = [t["name"] for t in write_server.get_tools_list()]

            assert "kb_link" not in read_names
            assert "kb_link" in write_names

            read_server.close()
            write_server.close()

    # ------------------------------------------------------------------
    # Entry type resolution (plugin subtype)
    # ------------------------------------------------------------------

    def test_kb_create_resolves_plugin_subtype(self, server_setup):
        """Test that create with a core type resolves to plugin subtype."""
        from unittest.mock import patch

        from pyrite.models import EventEntry

        # Create a mock plugin subclass of EventEntry
        class MockTimelineEvent(EventEntry):
            entry_type = "timeline_event"

        mock_plugin_types = {"timeline_event": MockTimelineEvent}

        server = server_setup["server"]

        with patch("pyrite.plugins.get_registry") as mock_reg:
            mock_reg.return_value.get_all_entry_types.return_value = mock_plugin_types
            # Also patch the hooks to avoid plugin lookup issues
            with patch.object(type(server.svc), "_run_hooks", side_effect=lambda _n, e, _c: e):
                result = server._dispatch_tool(
                    "kb_create",
                    {
                        "kb_name": "test-events",
                        "entry_type": "event",
                        "title": "Resolved Event",
                        "date": "2025-05-01",
                        "body": "Should resolve to timeline_event.",
                    },
                )

        assert result.get("created") is True
        entry_id = result["entry_id"]

        # Verify the entry was created — the type depends on whether
        # build_entry dispatches correctly for the resolved type
        get_result = server._dispatch_tool(
            "kb_get", {"entry_id": entry_id, "kb_name": "test-events"}
        )
        assert "entry" in get_result


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


class TestMCPPagination:
    """Tests for MCP tool pagination (limit/offset/has_more)."""

    @pytest.fixture
    def server_setup(self):
        """Create a test server with enough data for pagination tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"

            kb_path = tmpdir / "kb"
            kb_path.mkdir()

            kb = KBConfig(
                name="test-kb",
                path=kb_path,
                kb_type=KBType.EVENTS,
                description="Pagination test KB",
            )
            config = PyriteConfig(
                knowledge_bases=[kb], settings=Settings(index_path=db_path)
            )

            repo = KBRepository(kb)

            # Create 5 events with distinct dates and content
            for i in range(5):
                event = EventEntry.create(
                    date=f"2025-06-{10+i:02d}",
                    title=f"Pagination Event {i}",
                    body=f"Body for pagination event number {i}.",
                    importance=5,
                )
                event.tags = [f"tag-{i}", "common"]
                repo.save(event)

            # Create a target entry and 4 entries linking to it (for backlinks)
            target = NoteEntry(id="backlink-target", title="Backlink Target", body="Target entry.")
            target.tags = ["target"]
            repo.save(target)

            for i in range(4):
                source = NoteEntry(
                    id=f"backlink-source-{i}",
                    title=f"Backlink Source {i}",
                    body=f"Source {i} links to target.",
                )
                source.links = [Link(target=target.id, relation="related_to")]
                source.tags = ["source"]
                repo.save(source)

            server = PyriteMCPServer(config, tier="admin")
            server.index_mgr.index_all()

            yield {
                "server": server,
                "target_id": target.id,
            }
            server.close()

    # ------------------------------------------------------------------
    # kb_search pagination
    # ------------------------------------------------------------------

    def test_kb_search_pagination(self, server_setup):
        """Test kb_search offset returns different pages and has_more flag."""
        server = server_setup["server"]

        page1 = server._dispatch_tool(
            "kb_search", {"query": "pagination", "limit": 2, "offset": 0}
        )
        assert page1["count"] == 2
        assert page1["has_more"] is True

        page2 = server._dispatch_tool(
            "kb_search", {"query": "pagination", "limit": 2, "offset": 2}
        )
        assert page2["count"] == 2
        assert page2["has_more"] is True

        # IDs should differ between pages
        ids1 = {r["id"] for r in page1["results"]}
        ids2 = {r["id"] for r in page2["results"]}
        assert ids1.isdisjoint(ids2)

        # Last page
        page3 = server._dispatch_tool(
            "kb_search", {"query": "pagination", "limit": 2, "offset": 4}
        )
        assert page3["count"] == 1
        assert page3["has_more"] is False

    # ------------------------------------------------------------------
    # kb_timeline pagination
    # ------------------------------------------------------------------

    def test_kb_timeline_pagination(self, server_setup):
        """Test kb_timeline limit/offset and has_more flag."""
        server = server_setup["server"]

        page1 = server._dispatch_tool("kb_timeline", {"limit": 2, "offset": 0})
        assert page1["count"] == 2
        assert page1["has_more"] is True

        page2 = server._dispatch_tool("kb_timeline", {"limit": 2, "offset": 2})
        assert page2["count"] == 2
        assert page2["has_more"] is True

        # Different events on each page
        ids1 = {e["id"] for e in page1["events"]}
        ids2 = {e["id"] for e in page2["events"]}
        assert ids1.isdisjoint(ids2)

        # Large offset returns empty
        page_end = server._dispatch_tool("kb_timeline", {"limit": 10, "offset": 100})
        assert page_end["count"] == 0
        assert page_end["has_more"] is False

    # ------------------------------------------------------------------
    # kb_backlinks pagination
    # ------------------------------------------------------------------

    def test_kb_backlinks_pagination(self, server_setup):
        """Test kb_backlinks limit/offset and has_more flag."""
        server = server_setup["server"]
        target_id = server_setup["target_id"]

        page1 = server._dispatch_tool(
            "kb_backlinks",
            {"entry_id": target_id, "kb_name": "test-kb", "limit": 2, "offset": 0},
        )
        assert page1["backlink_count"] == 2
        assert page1["has_more"] is True

        page2 = server._dispatch_tool(
            "kb_backlinks",
            {"entry_id": target_id, "kb_name": "test-kb", "limit": 2, "offset": 2},
        )
        assert page2["backlink_count"] == 2
        assert page2["has_more"] is True

        ids1 = {b["id"] for b in page1["backlinks"]}
        ids2 = {b["id"] for b in page2["backlinks"]}
        assert ids1.isdisjoint(ids2)

        # Past the end
        page3 = server._dispatch_tool(
            "kb_backlinks",
            {"entry_id": target_id, "kb_name": "test-kb", "limit": 10, "offset": 10},
        )
        assert page3["backlink_count"] == 0
        assert page3["has_more"] is False

    # ------------------------------------------------------------------
    # kb_tags limit, offset, and prefix
    # ------------------------------------------------------------------

    def test_kb_tags_limit_and_prefix(self, server_setup):
        """Test kb_tags limit, offset, and prefix filtering at DB level."""
        server = server_setup["server"]

        # All tags
        all_tags = server._dispatch_tool("kb_tags", {"limit": 100})
        assert all_tags["tag_count"] >= 5  # tag-0..4 + common + target + source

        # Limit
        limited = server._dispatch_tool("kb_tags", {"limit": 2})
        assert limited["tag_count"] == 2
        assert limited["has_more"] is True

        # Offset
        page2 = server._dispatch_tool("kb_tags", {"limit": 2, "offset": 2})
        assert page2["tag_count"] == 2
        tags1 = {t["tag"] for t in limited["tags"]}
        tags2 = {t["tag"] for t in page2["tags"]}
        assert tags1.isdisjoint(tags2)

        # Prefix filter
        prefixed = server._dispatch_tool("kb_tags", {"prefix": "tag-", "limit": 100})
        assert prefixed["tag_count"] == 5
        for t in prefixed["tags"]:
            assert t["tag"].startswith("tag-")


class TestMCPValidation:
    """Tests for schema validation on MCP write paths."""

    @pytest.fixture
    def validated_server(self):
        """Server with a kb.yaml schema for validation testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"

            kb_path = tmpdir / "kb"
            kb_path.mkdir()

            # Write a kb.yaml with capture_lanes field (allow_other: true)
            from pyrite.utils.yaml import dump_yaml

            schema = {
                "name": "validated-kb",
                "types": {
                    "event": {
                        "fields": {
                            "capture_lanes": {
                                "type": "multi-select",
                                "allow_other": True,
                                "options": ["lane-a", "lane-b", "lane-c"],
                            },
                        },
                    },
                },
                "validation": {"enforce": True},
            }
            (kb_path / "kb.yaml").write_text(
                dump_yaml(schema), encoding="utf-8"
            )

            kb_config = KBConfig(
                name="val-kb",
                path=kb_path,
                kb_type=KBType.GENERIC,
                description="Validated KB",
            )
            config = PyriteConfig(
                knowledge_bases=[kb_config],
                settings=Settings(index_path=db_path),
            )
            server = PyriteMCPServer(config, tier="admin")
            server.index_mgr.index_all()
            yield {"server": server, "config": config, "kb_config": kb_config}
            server.close()

    def test_kb_create_with_capture_lane_warning(self, validated_server):
        """Creating with unknown capture lane returns result + warning."""
        server = validated_server["server"]
        result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "val-kb",
                "entry_type": "event",
                "title": "Lane Test Event",
                "date": "2025-03-01",
                "body": "Testing lanes.",
                "capture_lanes": ["lane-a", "new-lane"],
            },
        )
        assert result.get("created") is True
        assert "warnings" in result
        assert any(
            "new-lane" in str(w.get("got", ""))
            for w in result["warnings"]
        )

    def test_kb_update_validates_schema(self, validated_server):
        """_kb_update runs schema validation and surfaces warnings."""
        server = validated_server["server"]
        # First create an entry
        create_result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "val-kb",
                "entry_type": "note",
                "title": "Update Val Test",
                "body": "Will be updated.",
            },
        )
        assert create_result.get("created") is True
        entry_id = create_result["entry_id"]

        # Update should return updated: True (basic case)
        update_result = server._dispatch_tool(
            "kb_update",
            {
                "entry_id": entry_id,
                "kb_name": "val-kb",
                "body": "Updated body.",
            },
        )
        assert update_result.get("updated") is True


class TestMCPQATools:
    """Tests for QA validation MCP tools."""

    @pytest.fixture
    def qa_server_setup(self):
        """Create a test server with some bad data for QA testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"

            events_path = tmpdir / "events"
            events_path.mkdir()

            events_kb = KBConfig(
                name="qa-events",
                path=events_path,
                kb_type=KBType.EVENTS,
                description="QA test events",
            )
            config = PyriteConfig(
                knowledge_bases=[events_kb],
                settings=Settings(index_path=db_path),
            )

            # Create valid entries
            events_repo = KBRepository(events_kb)
            event = EventEntry.create(
                date="2025-01-10",
                title="Good Event",
                body="Valid event body.",
                importance=5,
            )
            events_repo.save(event)

            server = PyriteMCPServer(config, tier="admin")
            server.index_mgr.index_all()

            # Insert a bad entry directly in DB
            server.db._raw_conn.execute(
                "INSERT INTO entry (id, kb_name, entry_type, title, body, importance) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("no-title", "qa-events", "note", "", "Has body", 5),
            )
            server.db._raw_conn.commit()

            yield {"server": server, "config": config}
            server.close()

    def test_mcp_qa_validate_tool(self, qa_server_setup):
        """MCP kb_qa_validate returns issues."""
        result = qa_server_setup["server"]._dispatch_tool(
            "kb_qa_validate", {"kb_name": "qa-events"}
        )
        assert "issues" in result
        assert "count" in result
        # Should find the missing title issue
        rules = [i["rule"] for i in result["issues"]]
        assert "missing_title" in rules

    def test_mcp_qa_status_tool(self, qa_server_setup):
        """MCP kb_qa_status returns status dict."""
        result = qa_server_setup["server"]._dispatch_tool(
            "kb_qa_status", {"kb_name": "qa-events"}
        )
        assert "total_entries" in result
        assert "total_issues" in result
        assert "issues_by_severity" in result
        assert "issues_by_rule" in result
        assert result["total_entries"] > 0


class TestMCPPostSaveValidation:
    """Tests for post-save QA validation on MCP write paths."""

    @pytest.fixture
    def qa_write_server(self):
        """Server for testing post-save QA validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"

            kb_path = tmpdir / "kb"
            kb_path.mkdir()

            from pyrite.utils.yaml import dump_yaml

            schema = {
                "name": "qa-write-kb",
                "types": {"note": {}},
            }
            (kb_path / "kb.yaml").write_text(
                dump_yaml(schema), encoding="utf-8"
            )

            kb_config = KBConfig(
                name="qa-kb",
                path=kb_path,
                kb_type=KBType.GENERIC,
                description="QA write test KB",
            )
            config = PyriteConfig(
                knowledge_bases=[kb_config],
                settings=Settings(index_path=db_path),
            )
            server = PyriteMCPServer(config, tier="write")
            server.index_mgr.index_all()
            yield {"server": server, "kb_path": kb_path}
            server.close()

    @pytest.fixture
    def qa_on_write_server(self):
        """Server with qa_on_write: true in kb.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"

            kb_path = tmpdir / "kb"
            kb_path.mkdir()

            from pyrite.utils.yaml import dump_yaml

            schema = {
                "name": "qa-auto-kb",
                "types": {"note": {}},
                "validation": {"qa_on_write": True},
            }
            (kb_path / "kb.yaml").write_text(
                dump_yaml(schema), encoding="utf-8"
            )

            kb_config = KBConfig(
                name="qa-auto",
                path=kb_path,
                kb_type=KBType.GENERIC,
                description="QA auto-validate KB",
            )
            config = PyriteConfig(
                knowledge_bases=[kb_config],
                settings=Settings(index_path=db_path),
            )
            server = PyriteMCPServer(config, tier="write")
            server.index_mgr.index_all()
            yield {"server": server, "kb_path": kb_path}
            server.close()

    def test_kb_create_with_validate_clean(self, qa_write_server):
        """Valid entry with validate=True returns no qa_issues."""
        server = qa_write_server["server"]
        result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "qa-kb",
                "entry_type": "note",
                "title": "Clean Entry",
                "body": "This entry has a proper body.",
                "validate": True,
            },
        )
        assert result.get("created") is True
        assert "qa_issues" not in result

    def test_kb_create_with_validate_has_issues(self, qa_write_server):
        """Empty body with validate=True returns qa_issues."""
        server = qa_write_server["server"]
        result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "qa-kb",
                "entry_type": "note",
                "title": "Empty Body Entry",
                "body": "",
                "validate": True,
            },
        )
        assert result.get("created") is True
        assert "qa_issues" in result
        rules = [i["rule"] for i in result["qa_issues"]]
        assert "empty_body" in rules

    def test_kb_update_with_validate(self, qa_write_server):
        """Update with validate=True returns qa_issues when entry has problems."""
        server = qa_write_server["server"]
        # Create an entry first
        create_result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "qa-kb",
                "entry_type": "note",
                "title": "Will Update",
                "body": "Original body.",
            },
        )
        entry_id = create_result["entry_id"]

        # Update to empty body with validation
        update_result = server._dispatch_tool(
            "kb_update",
            {
                "entry_id": entry_id,
                "kb_name": "qa-kb",
                "body": "",
                "validate": True,
            },
        )
        assert update_result.get("updated") is True
        assert "qa_issues" in update_result
        rules = [i["rule"] for i in update_result["qa_issues"]]
        assert "empty_body" in rules

    def test_kb_create_without_validate(self, qa_write_server):
        """Default create (no validate param) returns no qa_issues key."""
        server = qa_write_server["server"]
        result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "qa-kb",
                "entry_type": "note",
                "title": "No Validate Entry",
                "body": "",
            },
        )
        assert result.get("created") is True
        assert "qa_issues" not in result

    def test_kb_create_qa_on_write_kb(self, qa_on_write_server):
        """KB with qa_on_write: true auto-validates even without explicit param."""
        server = qa_on_write_server["server"]
        result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "qa-auto",
                "entry_type": "note",
                "title": "Auto Validate Entry",
                "body": "",
            },
        )
        assert result.get("created") is True
        assert "qa_issues" in result
        rules = [i["rule"] for i in result["qa_issues"]]
        assert "empty_body" in rules

    def test_kb_create_qa_on_write_kb_clean(self, qa_on_write_server):
        """KB with qa_on_write: true, valid entry returns no qa_issues."""
        server = qa_on_write_server["server"]
        result = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "qa-auto",
                "entry_type": "note",
                "title": "Clean Auto Entry",
                "body": "This entry has proper content.",
            },
        )
        assert result.get("created") is True
        assert "qa_issues" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
