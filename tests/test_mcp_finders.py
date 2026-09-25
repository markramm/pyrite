"""The MCP protocol finders' own rules, independent of scoping (#380).

`kb_find_by_*` / `kb_find_overdue` refuse an empty required argument, clamp
`limit` to 200 and pass `offset` through; the `pyrite://kbs/{kb}/entries`
resource lists a KB's entries. Characterizes the move of these handlers
from `self.db` onto TaskService / KBService.
"""

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.mcp_server import PyriteMCPServer
from pyrite.storage.database import PyriteDB


@pytest.fixture
def server(tmp_path):
    (tmp_path / "kb").mkdir()
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="kb", path=tmp_path / "kb", kb_type="generic")],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(config.settings.index_path)
    db.register_kb("kb", "generic", str(tmp_path / "kb"))
    for i in range(3):
        db.upsert_entry(
            {
                "id": f"t{i}",
                "kb_name": "kb",
                "entry_type": "task",
                "title": f"T{i}",
                "body": "",
                "assignee": "agent:x",
                "status": "open",
                "due_date": "2020-01-01",
                "location": "Springfield",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )
    db.close()
    srv = PyriteMCPServer(config=config, tier="read")
    yield srv
    srv.close()


@pytest.mark.parametrize(
    ("tool", "arg"),
    [
        ("kb_find_by_assignee", "assignee"),
        ("kb_find_by_status", "status"),
        ("kb_find_by_location", "location"),
    ],
)
def test_empty_required_argument_is_refused(server, tool, arg):
    out = server._dispatch_tool(tool, {arg: ""}, client_id="t")
    assert out["error_code"] == "VALIDATION_FAILED"
    assert f"{arg} is required" in out["error"]


@pytest.mark.parametrize(
    ("tool", "args", "method"),
    [
        ("kb_find_by_assignee", {"assignee": "agent:x"}, "find_by_assignee"),
        ("kb_find_by_status", {"status": "open"}, "find_by_status"),
        ("kb_find_by_location", {"location": "Spring"}, "find_by_location"),
        ("kb_find_overdue", {}, "find_overdue"),
    ],
)
def test_limit_is_clamped_and_offset_passed(server, monkeypatch, tool, args, method):
    real = getattr(PyriteDB, method)
    seen = {}

    def spy(self, *a, **kw):
        seen.update(kw)
        return real(self, *a, **kw)

    monkeypatch.setattr(PyriteDB, method, spy)
    out = server._dispatch_tool(tool, {**args, "limit": 999, "offset": 1}, client_id="t")
    assert seen["limit"] == 200
    assert seen["offset"] == 1
    assert out["count"] == 2


def test_kb_entries_resource_lists_entries(server):
    import json

    out = server._read_resource("pyrite://kbs/kb/entries")
    rows = json.loads(out["contents"][0]["text"])
    assert sorted(r["id"] for r in rows) == ["t0", "t1", "t2"]
