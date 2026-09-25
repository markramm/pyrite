"""pyrite/ui/data.py (the Streamlit UI's data layer), characterized for #380.

Streamlit is an optional extra and is not installed in the test
environment, so a stub stands in for it: its cache decorators become
pass-throughs, which leaves the functions' own behaviour to test.
"""

import sys
import types
from unittest.mock import patch

import pytest

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models.core_types import EventEntry, NoteEntry
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager


def _passthrough(*args, **kwargs):
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]
    return lambda fn: fn


@pytest.fixture
def ui(tmp_path, monkeypatch):
    st = types.ModuleType("streamlit")
    st.cache_resource = _passthrough
    st.cache_data = _passthrough
    st.cache_data.clear = lambda: None
    st.error = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "streamlit", st)
    monkeypatch.delitem(sys.modules, "pyrite.ui.data", raising=False)

    kb_path = tmp_path / "kb"
    kb_path.mkdir()
    NoteEntry(id="a", title="A", body="links to [[b]]", tags=["t1"]).save(kb_path / "a.md")
    NoteEntry(id="b", title="B", body="plain", tags=["t1", "t2"]).save(kb_path / "b.md")
    event = EventEntry.create(date="2025-01-10", title="Ev", body="e", importance=7)
    event.save(kb_path / f"{event.id}.md")
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="kb", path=kb_path, kb_type=KBType.GENERIC)],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(config.settings.index_path)
    IndexManager(db, config).index_all()
    db.close()

    with patch("pyrite.config.load_config", return_value=config):
        import pyrite.ui.data as data

        with patch.object(data, "load_config", return_value=config):
            yield data, event.id


def test_kb_list(ui):
    data, _ = ui
    assert data.get_kb_list() == [
        {
            "name": "kb",
            "type": KBType.GENERIC,
            "path": str(data._get_config().knowledge_bases[0].path),
            "entries": 3,
            "indexed": True,
        }
    ]


def test_timeline_and_tags(ui):
    data, event_id = ui
    assert [e["id"] for e in data.get_timeline()] == [event_id]
    assert data.get_timeline(min_importance=8) == []
    tags = {t["name"]: t["count"] for t in data.get_tags()}
    assert tags == {"t1": 2, "t2": 1}
    assert data.get_tags(kb_name="All KBs", limit=1)[0]["name"] == "t1"


def test_entry_with_links(ui):
    data, _ = ui
    for kb in ("kb", None, "All KBs"):
        entry = data.get_entry("a", kb)
        assert entry["title"] == "A"
        assert [link["id"] for link in entry["outlinks"]] == ["b"]
        assert entry["backlinks"] == []
    assert [link["id"] for link in data.get_entry("b")["backlinks"]] == ["a"]
    assert data.get_entry("missing") is None


def test_entry_graph(ui):
    data, _ = ui
    graph = data.get_entry_graph("a", "kb")
    assert {n["id"] for n in graph["nodes"]} == {"a", "b"}
    assert graph["edges"] == [{"source": "a", "target": "b", "label": "wikilink"}]
    assert data.get_entry_graph("missing", "kb") == {"nodes": [], "edges": []}
