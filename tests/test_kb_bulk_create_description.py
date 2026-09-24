"""Bulk create's advertised schema must allow per-entry title failures (#95)."""

from pathlib import Path

import jsonschema
import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.mcp_server import PyriteMCPServer
from pyrite.server.tool_schemas import WRITE_TOOLS


@pytest.fixture
def bulk_server(tmp_path):
    kb_path = tmp_path / "kb"
    kb_path.mkdir()
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="bulk", path=kb_path, kb_type="generic")],
        settings=Settings(index_path=tmp_path / "index.db", auto_embed=False),
    )
    server = PyriteMCPServer(config, tier="write")
    server.index_mgr.index_all()
    try:
        yield server
    finally:
        server.close()


def call_bulk(server, entries, kb_name="bulk"):
    args = {"kb_name": kb_name, "entries": entries}
    # Direct handler tests miss the parameter validation that rejected #95.
    jsonschema.validate(args, WRITE_TOOLS["kb_bulk_create"]["inputSchema"])
    return server._dispatch_tool("kb_bulk_create", args)


@pytest.mark.parametrize("bad", [{"body": "Missing title"}, {"title": ""}])
def test_one_bad_title_does_not_reject_four_valid_entries(bulk_server, bad):
    entries = [{"title": f"Bulk note {i}", "body": f"Body {i}"} for i in range(5)]
    entries[2] = bad
    result = call_bulk(bulk_server, entries)
    assert (result["total"], result["created"], result["failed"]) == (5, 4, 1)
    assert len(result["results"]) == len(entries)
    for i, item in enumerate(result["results"]):
        if i == 2:
            assert item["created"] is False
            assert "title" in item["error"]
        else:
            assert item["created"] is True
            indexed = bulk_server.db.get_entry(item["entry_id"], "bulk")
            assert indexed["title"] == entries[i]["title"]
            assert entries[i]["body"] in Path(indexed["file_path"]).read_text()


def test_all_bad_titles_return_ordered_failures(bulk_server):
    result = call_bulk(bulk_server, [{}, {"title": ""}, {"body": "No title"}])
    assert (result["created"], result["failed"]) == (0, 3)
    assert len(result["results"]) == 3
    assert all(not row["created"] and "title" in row["error"] for row in result["results"])


def test_deeper_validation_failure_stays_per_entry(bulk_server, monkeypatch):
    from pyrite.services import kb_service

    original = kb_service.build_entry

    def validate_entry(*args, **kwargs):
        if kwargs["title"] == "Bad":
            raise ValueError("Entry validation failed")
        return original(*args, **kwargs)

    monkeypatch.setattr(kb_service, "build_entry", validate_entry)
    result = call_bulk(bulk_server, [{"title": "Good"}, {"title": "Bad"}])
    assert (result["created"], result["failed"]) == (1, 1)
    assert result["results"][0]["created"] is True
    assert result["results"][1]["created"] is False


def test_empty_batch_still_fails(bulk_server):
    assert "error" in call_bulk(bulk_server, [])


def test_over_limit_still_rejected_by_schema(bulk_server):
    with pytest.raises(jsonschema.ValidationError):
        call_bulk(bulk_server, [{"title": f"Entry {i}"} for i in range(51)])
    assert bulk_server.db.list_entries(kb_name="bulk") == []


@pytest.mark.parametrize("read_only", [False, True])
def test_unavailable_kb_still_rejects_whole_batch(bulk_server, read_only):
    if read_only:
        bulk_server.config.get_kb("bulk").read_only = True
    result = call_bulk(bulk_server, [{"title": "Good"}, {}], "bulk" if read_only else "missing")
    assert "error" in result
    assert bulk_server.db.list_entries(kb_name="bulk") == []


def test_description_explains_ordered_per_entry_results():
    description = WRITE_TOOLS["kb_bulk_create"]["description"].lower()
    assert "missing or empty title" in description
    assert "input order" in description
