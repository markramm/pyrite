"""Tests for Cascade timeline static export."""

import json
from pathlib import Path

import pytest

from pyrite.config import PyriteConfig, Settings, KBConfig
from pyrite.storage.database import PyriteDB
from pyrite.services.kb_service import KBService


@pytest.fixture
def setup(tmp_path):
    """Set up a KB with timeline events for export testing."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    kb = KBConfig(name="test", path=kb_path, kb_type="cascade-timeline")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    svc = KBService(config, db)

    svc.create_entry("test", "event-1", "First event", "timeline_event",
                     date="2025-01-20", actors=["Donald Trump", "FBI"],
                     tags=["executive-power", "judiciary"],
                     importance=8)
    svc.create_entry("test", "event-2", "Second event", "timeline_event",
                     date="2025-02-01", actors=["Donald Trump", "Elon Musk"],
                     tags=["executive-power"],
                     importance=7)
    svc.create_entry("test", "event-3", "Third event", "timeline_event",
                     date="2025-03-01", actors=["FBI", "Pete Hegseth"],
                     tags=["judiciary"],
                     importance=5)

    yield {"db": db, "svc": svc, "config": config, "kb_path": kb_path, "tmp_path": tmp_path}
    db.close()


class TestStaticExport:
    """Test static JSON export for viewer consumption."""

    def test_timeline_json_structure(self, setup):
        from pyrite_cascade.static_export import export_timeline

        result = export_timeline(setup["db"], "test")
        timeline = result["timeline"]
        assert isinstance(timeline, list)
        assert len(timeline) == 3
        # Should be sorted by date
        dates = [e["date"] for e in timeline]
        assert dates == sorted(dates)

    def test_timeline_event_fields(self, setup):
        from pyrite_cascade.static_export import export_timeline

        result = export_timeline(setup["db"], "test")
        event = next(e for e in result["timeline"] if e["id"] == "event-1")
        assert event["title"] == "First event"
        assert event["date"] == "2025-01-20"
        assert "Donald Trump" in event["actors"]
        assert "FBI" in event["actors"]
        assert "executive-power" in event["tags"]

    def test_actors_json_structure(self, setup):
        from pyrite_cascade.static_export import export_timeline

        result = export_timeline(setup["db"], "test")
        actors = result["actors"]
        assert isinstance(actors, list)
        # Donald Trump appears in 2 events
        trump = next(a for a in actors if a["name"] == "Donald Trump")
        assert trump["count"] == 2
        # Should be sorted by count descending
        counts = [a["count"] for a in actors]
        assert counts == sorted(counts, reverse=True)

    def test_tags_json_structure(self, setup):
        from pyrite_cascade.static_export import export_timeline

        result = export_timeline(setup["db"], "test")
        tags = result["tags"]
        assert isinstance(tags, list)
        exec_power = next(t for t in tags if t["name"] == "executive-power")
        assert exec_power["count"] == 2
        counts = [t["count"] for t in tags]
        assert counts == sorted(counts, reverse=True)

    def test_stats_json_structure(self, setup):
        from pyrite_cascade.static_export import export_timeline

        result = export_timeline(setup["db"], "test")
        stats = result["stats"]
        assert stats["total_events"] == 3
        assert stats["date_range"]["start"] == "2025-01-20"
        assert stats["date_range"]["end"] == "2025-03-01"
        assert "generated" in stats

    def test_write_to_directory(self, setup):
        from pyrite_cascade.static_export import export_timeline, write_export

        result = export_timeline(setup["db"], "test")
        out_dir = setup["tmp_path"] / "export"
        write_export(result, out_dir)

        assert (out_dir / "timeline.json").exists()
        assert (out_dir / "timeline-index.json").exists()
        assert (out_dir / "actors.json").exists()
        assert (out_dir / "tags.json").exists()
        assert (out_dir / "stats.json").exists()

        # Verify JSON is valid
        timeline = json.loads((out_dir / "timeline.json").read_text())
        assert len(timeline) == 3

        # Index should have same events but no body
        index = json.loads((out_dir / "timeline-index.json").read_text())
        assert len(index) == 3
        assert "body" not in index[0]
        assert index[0]["title"] == timeline[0]["title"]

    def test_date_filter(self, setup):
        from pyrite_cascade.static_export import export_timeline

        result = export_timeline(setup["db"], "test",
                                 from_date="2025-02-01", to_date="2025-02-28")
        assert len(result["timeline"]) == 1
        assert result["timeline"][0]["id"] == "event-2"

    def test_sources_included_in_export(self, setup):
        """Sources stored in the source table should appear in export."""
        from pyrite_cascade.static_export import export_timeline

        # Create an event with sources via the service layer (which writes to source table)
        setup["svc"].create_entry(
            "test", "event-sourced", "Sourced Event", "timeline_event",
            date="2025-04-01", importance=7,
            sources=[
                {"title": "Washington Post", "url": "https://wapo.com/article", "outlet": "WaPo"},
                {"title": "NPR Report", "url": "https://npr.org/report", "outlet": "NPR"},
            ],
        )

        result = export_timeline(setup["db"], "test")
        event = next(e for e in result["timeline"] if e["id"] == "event-sourced")
        assert len(event["sources"]) == 2
        assert event["sources"][0]["title"] == "Washington Post"
        assert result["stats"]["total_sources"] >= 2

    def test_min_importance_filter(self, setup):
        from pyrite_cascade.static_export import export_timeline

        result = export_timeline(setup["db"], "test", min_importance=7)
        assert len(result["timeline"]) == 2
        ids = {e["id"] for e in result["timeline"]}
        assert "event-3" not in ids  # importance 5 < 7
