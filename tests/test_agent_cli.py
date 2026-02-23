"""
Tests for Agent CLIs (crk-read and crk).

Tests both JSON output format and command functionality.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import EventEntry
from pyrite.models.core_types import PersonEntry
from pyrite.read_cli import EXIT_NOT_FOUND, EXIT_OK, ReadOnlyCLI
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository
from pyrite.write_cli import FullAccessCLI


class TestReadOnlyCLI:
    """Tests for crk-read (ReadOnlyCLI)."""

    @pytest.fixture
    def setup(self):
        """Create test environment with sample data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"

            events_path = tmpdir / "events"
            events_path.mkdir()

            research_path = tmpdir / "research"
            research_path.mkdir()
            (research_path / "actors").mkdir()

            events_kb = KBConfig(
                name="test-events",
                path=events_path,
                kb_type=KBType.EVENTS,
            )

            research_kb = KBConfig(
                name="test-research",
                path=research_path,
                kb_type=KBType.RESEARCH,
            )

            config = PyriteConfig(
                knowledge_bases=[events_kb, research_kb], settings=Settings(index_path=db_path)
            )

            # Create sample entries
            events_repo = KBRepository(events_kb)
            for i in range(3):
                event = EventEntry.create(
                    date=f"2025-01-{10+i:02d}",
                    title=f"Test Event {i}",
                    body=f"Body for event {i} about immigration policy.",
                    importance=5 + i,
                )
                event.tags = ["test", "immigration"]
                event.participants = ["Stephen Miller", "Tom Homan"]
                events_repo.save(event)

            research_repo = KBRepository(research_kb)
            actor = PersonEntry.create(
                name="Stephen Miller", role="Immigration policy architect", importance=9
            )
            actor.body = "Stephen Miller biography."
            actor.tags = ["trump-admin", "immigration"]
            research_repo.save(actor)

            cli = ReadOnlyCLI()
            cli.config = config
            cli.db = PyriteDB(db_path)

            index_mgr = IndexManager(cli.db, config)
            index_mgr.index_all()

            yield {"cli": cli, "config": config}

            cli.db.close()

    def test_output_json_format(self, setup):
        """Test that output is valid JSON with expected structure."""
        import io
        from contextlib import redirect_stdout

        cli = setup["cli"]
        args = type("Args", (), {})()

        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli.cmd_list(args)

        output = f.getvalue()
        result = json.loads(output)

        assert result["ok"] is True
        assert result["code"] == 0
        assert "data" in result
        assert "kbs" in result["data"]

    def test_list_kbs(self, setup):
        """Test listing knowledge bases."""
        import io
        from contextlib import redirect_stdout

        cli = setup["cli"]
        args = type("Args", (), {})()

        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli.cmd_list(args)

        assert exit_code == EXIT_OK
        result = json.loads(f.getvalue())
        assert result["data"]["total"] == 2

    def test_search(self, setup):
        """Test search command."""
        import io
        from contextlib import redirect_stdout

        cli = setup["cli"]
        args = type(
            "Args",
            (),
            {
                "query": "immigration",
                "kb": None,
                "type": None,
                "tags": None,
                "date_from": None,
                "date_to": None,
                "limit": 20,
            },
        )()

        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli.cmd_search(args)

        assert exit_code == EXIT_OK
        result = json.loads(f.getvalue())
        assert result["data"]["count"] >= 1

    def test_get_entry(self, setup):
        """Test getting entry by ID."""
        import io
        from contextlib import redirect_stdout

        cli = setup["cli"]

        # First search to get an ID
        search_args = type(
            "Args",
            (),
            {
                "query": "Stephen Miller",
                "kb": "test-research",
                "type": None,
                "tags": None,
                "date_from": None,
                "date_to": None,
                "limit": 5,
            },
        )()

        f = io.StringIO()
        with redirect_stdout(f):
            cli.cmd_search(search_args)

        search_result = json.loads(f.getvalue())
        if search_result["data"]["count"] > 0:
            entry_id = search_result["data"]["results"][0]["id"]

            args = type(
                "Args", (), {"entry_id": entry_id, "kb": "test-research", "with_links": False}
            )()

            f = io.StringIO()
            with redirect_stdout(f):
                exit_code = cli.cmd_get(args)

            assert exit_code == EXIT_OK
            result = json.loads(f.getvalue())
            assert "entry" in result["data"]

    def test_get_not_found(self, setup):
        """Test getting non-existent entry."""
        import io
        from contextlib import redirect_stdout

        cli = setup["cli"]
        args = type(
            "Args", (), {"entry_id": "nonexistent-entry-id", "kb": None, "with_links": False}
        )()

        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli.cmd_get(args)

        assert exit_code == EXIT_NOT_FOUND
        result = json.loads(f.getvalue())
        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"

    def test_timeline(self, setup):
        """Test timeline query."""
        import io
        from contextlib import redirect_stdout

        cli = setup["cli"]
        args = type(
            "Args",
            (),
            {
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
                "min_importance": None,
                "actor": None,
                "limit": 50,
            },
        )()

        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli.cmd_timeline(args)

        assert exit_code == EXIT_OK
        result = json.loads(f.getvalue())
        assert "events" in result["data"]

    def test_tags(self, setup):
        """Test getting tags."""
        import io
        from contextlib import redirect_stdout

        cli = setup["cli"]
        args = type("Args", (), {"kb": None, "limit": 100})()

        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli.cmd_tags(args)

        assert exit_code == EXIT_OK
        result = json.loads(f.getvalue())
        assert "tags" in result["data"]

    def test_stats(self, setup):
        """Test getting stats."""
        import io
        from contextlib import redirect_stdout

        cli = setup["cli"]
        args = type("Args", (), {})()

        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli.cmd_stats(args)

        assert exit_code == EXIT_OK
        result = json.loads(f.getvalue())
        assert "total_entries" in result["data"]


class TestFullAccessCLI:
    """Tests for crk (FullAccessCLI) write operations."""

    @pytest.fixture
    def setup(self):
        """Create test environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"

            events_path = tmpdir / "events"
            events_path.mkdir()

            events_kb = KBConfig(
                name="test-events",
                path=events_path,
                kb_type=KBType.EVENTS,
            )

            config = PyriteConfig(
                knowledge_bases=[events_kb], settings=Settings(index_path=db_path)
            )

            cli = FullAccessCLI()
            cli.config = config
            cli.db = PyriteDB(db_path)

            IndexManager(cli.db, config).index_all()

            yield {"cli": cli, "config": config, "events_kb": events_kb}

            cli.db.close()

    def test_create_event(self, setup):
        """Test creating an event."""
        import io
        from contextlib import redirect_stdout

        cli = setup["cli"]
        args = type(
            "Args",
            (),
            {
                "kb": "test-events",
                "type": "event",
                "title": "New Test Event",
                "body": "Test body.",
                "date": "2025-02-01",
                "importance": 7,
                "tags": "new,test",
                "actors": "Test Actor",
                "role": None,
            },
        )()

        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli.cmd_create(args)

        assert exit_code == EXIT_OK
        result = json.loads(f.getvalue())
        assert result["data"]["created"] is True
        assert "id" in result["data"]

    def test_index_stats(self, setup):
        """Test index stats."""
        import io
        from contextlib import redirect_stdout

        cli = setup["cli"]
        args = type("Args", (), {})()

        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli.cmd_index_stats(args)

        assert exit_code == EXIT_OK

    def test_index_health(self, setup):
        """Test index health."""
        import io
        from contextlib import redirect_stdout

        cli = setup["cli"]
        args = type("Args", (), {"verbose": False})()

        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli.cmd_index_health(args)

        assert exit_code == EXIT_OK
        result = json.loads(f.getvalue())
        assert "healthy" in result["data"]


class TestErrorHandling:
    """Test error handling."""

    def test_structured_error_format(self):
        """Test that errors have proper structure."""
        import io
        from contextlib import redirect_stdout

        cli = ReadOnlyCLI()

        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli.error(
                code="TEST_ERROR",
                message="Test error message",
                hint="Fix it this way",
                exit_code=99,
            )

        result = json.loads(f.getvalue())
        assert result["ok"] is False
        assert result["code"] == 99
        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["message"] == "Test error message"
        assert result["error"]["hint"] == "Fix it this way"


class TestCLIIntegration:
    """Integration tests with command-line parsing."""

    def test_read_cli_help(self):
        """Test that crk-read --help works."""
        from pyrite.read_cli import main

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["crk-read", "--help"]):
                main()
        assert exc_info.value.code == 0

    def test_write_cli_help(self):
        """Test that crk --help works."""
        from pyrite.write_cli import main

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["crk", "--help"]):
                main()
        assert exc_info.value.code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
