"""Tests for software KB orient supplement."""

import json
import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.plugins.registry import PluginRegistry, get_registry
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def software_kb_setup(tmp_path, monkeypatch):
    """Set up a software-type KB with the software_kb plugin registered."""
    kb_dir = tmp_path / "software-kb"
    kb_dir.mkdir()

    # Create board config
    board_yaml = kb_dir / "board.yaml"
    board_yaml.write_text(
        "lanes:\n"
        "  - name: Backlog\n"
        "    statuses: [proposed, accepted]\n"
        "  - name: Ready\n"
        "    statuses: [ready]\n"
        "  - name: In Progress\n"
        "    statuses: [in_progress]\n"
        "    wip_limit: 5\n"
        "  - name: Review\n"
        "    statuses: [review]\n"
        "    wip_limit: 3\n"
        "  - name: Done\n"
        "    statuses: [done]\n"
        "wip_policy: warn\n"
    )

    db_path = tmp_path / "index.db"
    kb_config = KBConfig(
        name="test-sw",
        path=kb_dir,
        kb_type="software",
        description="Test software KB",
    )
    config = PyriteConfig(
        knowledge_bases=[kb_config],
        settings=Settings(index_path=db_path),
    )
    db = PyriteDB(db_path)
    svc = KBService(config, db)

    # Register software_kb plugin
    from pyrite_software_kb.plugin import SoftwareKBPlugin
    from pyrite.plugins.context import PluginContext

    plugin = SoftwareKBPlugin()
    ctx = PluginContext(config=config, db=db)
    plugin.set_context(ctx)

    registry = get_registry()
    registry.register(plugin)

    yield {
        "config": config,
        "db": db,
        "svc": svc,
        "plugin": plugin,
        "kb_dir": kb_dir,
    }
    db.close()


def _insert_entry(db, entry_id, kb_name, entry_type, title, status="", priority="", metadata=None):
    """Insert a minimal entry row directly (FK checks temporarily disabled)."""
    meta_json = json.dumps(metadata) if metadata else None
    conn = db._raw_conn
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(
        "INSERT INTO entry (id, kb_name, entry_type, title, status, priority, metadata, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
        [entry_id, kb_name, entry_type, title, status, priority, meta_json],
    )
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def test_orient_includes_software_supplement(software_kb_setup):
    """Orient for a software KB returns 'software' key with expected sub-keys."""
    svc = software_kb_setup["svc"]
    db = software_kb_setup["db"]

    # Add one backlog item so there's data
    _insert_entry(
        db,
        "item-1",
        "test-sw",
        "backlog_item",
        "Fix bug",
        status="in_progress",
        priority="high",
        metadata={"kind": "bug", "status": "in_progress", "priority": "high"},
    )

    result = svc.orient("test-sw")
    assert "software" in result
    sw = result["software"]
    assert "board_summary" in sw
    assert "in_progress" in sw
    assert "review_queue" in sw
    assert "recent_adrs" in sw
    assert "top_components" in sw
    assert "recommended_next" in sw


def test_orient_no_software_for_generic_kb(tmp_path, monkeypatch):
    """Orient for a non-software KB has no 'software' key."""
    kb_dir = tmp_path / "generic-kb"
    kb_dir.mkdir()
    db_path = tmp_path / "index.db"
    kb_config = KBConfig(
        name="test-generic",
        path=kb_dir,
        kb_type="generic",
        description="Generic KB",
    )
    config = PyriteConfig(
        knowledge_bases=[kb_config],
        settings=Settings(index_path=db_path),
    )
    db = PyriteDB(db_path)
    svc = KBService(config, db)
    try:
        result = svc.orient("test-generic")
        assert "software" not in result
    finally:
        db.close()


def test_software_supplement_board_summary(software_kb_setup):
    """Board summary has lane data with counts."""
    svc = software_kb_setup["svc"]
    db = software_kb_setup["db"]

    _insert_entry(
        db,
        "item-a",
        "test-sw",
        "backlog_item",
        "Task A",
        status="proposed",
        priority="medium",
        metadata={"kind": "feature", "status": "proposed"},
    )
    _insert_entry(
        db,
        "item-b",
        "test-sw",
        "backlog_item",
        "Task B",
        status="in_progress",
        priority="high",
        metadata={"kind": "bug", "status": "in_progress"},
    )
    _insert_entry(
        db,
        "item-c",
        "test-sw",
        "backlog_item",
        "Task C",
        status="review",
        priority="medium",
        metadata={"kind": "feature", "status": "review"},
    )

    result = svc.orient("test-sw")
    sw = result["software"]
    board = sw["board_summary"]

    # Should have lanes
    assert len(board) >= 3
    lane_names = [l["name"] for l in board]
    assert "Backlog" in lane_names
    assert "In Progress" in lane_names
    assert "Review" in lane_names

    # Check counts
    ip_lane = next(l for l in board if l["name"] == "In Progress")
    assert ip_lane["count"] == 1
    assert ip_lane["wip_limit"] == 5
    assert ip_lane["over_limit"] is False

    rv_lane = next(l for l in board if l["name"] == "Review")
    assert rv_lane["count"] == 1

    # Check in_progress and review_queue lists
    assert len(sw["in_progress"]) == 1
    assert sw["in_progress"][0]["id"] == "item-b"
    assert len(sw["review_queue"]) == 1
    assert sw["review_queue"][0]["id"] == "item-c"


def test_software_supplement_graceful_empty(software_kb_setup):
    """Software supplement with empty KB returns empty lists, not errors."""
    svc = software_kb_setup["svc"]
    result = svc.orient("test-sw")
    sw = result["software"]
    assert sw["in_progress"] == []
    assert sw["review_queue"] == []
    assert sw["recent_adrs"] == []
    assert sw["top_components"] == []
    assert sw["recommended_next"] is None


def test_software_supplement_recent_adrs(software_kb_setup):
    """Recent ADRs appear in supplement."""
    db = software_kb_setup["db"]
    svc = software_kb_setup["svc"]

    _insert_entry(
        db,
        "adr-001",
        "test-sw",
        "adr",
        "Use REST for API",
        metadata={"adr_number": 1, "status": "accepted", "date": "2025-01-15"},
    )
    _insert_entry(
        db,
        "adr-002",
        "test-sw",
        "adr",
        "Adopt TypeScript",
        metadata={"adr_number": 2, "status": "accepted", "date": "2025-02-01"},
    )

    result = svc.orient("test-sw")
    adrs = result["software"]["recent_adrs"]
    assert len(adrs) == 2
    assert any(a["id"] == "adr-001" for a in adrs)
    assert any(a["adr_number"] == 2 for a in adrs)


def test_software_supplement_components(software_kb_setup):
    """Components appear in supplement."""
    db = software_kb_setup["db"]
    svc = software_kb_setup["svc"]

    _insert_entry(
        db,
        "comp-api",
        "test-sw",
        "component",
        "API Server",
        metadata={"path": "pyrite/server/", "kind": "service"},
    )

    result = svc.orient("test-sw")
    comps = result["software"]["top_components"]
    assert len(comps) == 1
    assert comps[0]["id"] == "comp-api"
    assert comps[0]["path"] == "pyrite/server/"
    assert comps[0]["kind"] == "service"
