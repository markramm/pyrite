"""Every entry type must round-trip frontmatter keys it does not declare.

Typed classes (core and plugin) re-emitted only the keys they knew, so a
load -> save through any of them deleted everything else: `pyrite update -f
status=done` on a backlog item stripped `milestone:` and `created:` (2026-09-17,
twice). Only GenericEntry and TaskEntry collected unknown keys. The guarantee
belongs in the base class, so this test runs over every registered type.
"""

import pytest

import pyrite.models  # noqa: F401  (registers core types)
from pyrite.models.core_types import ENTRY_TYPE_REGISTRY, entry_from_frontmatter
from pyrite.plugins import get_registry

EXTRAS = {
    "milestone": "0.13",
    "github_issue": 15,
    "custom_list": ["a", "b"],
    "custom_map": {"nested": {"deep": True}},
}


def _all_types() -> list[str]:
    reg = get_registry()
    reg.discover()
    names = set(ENTRY_TYPE_REGISTRY)
    for plugin in reg._plugins.values():
        try:
            names.update(plugin.get_entry_types())
        except Exception:  # a plugin that fails to list types is not this test's concern
            pass
    return sorted(names)


@pytest.mark.parametrize("entry_type", _all_types())
def test_unknown_keys_survive_load_then_save(entry_type):
    meta = {"id": "rt-probe", "title": "Round trip", "type": entry_type, **EXTRAS}
    entry = entry_from_frontmatter(meta, "body")
    out = entry.to_frontmatter()
    for key, value in EXTRAS.items():
        assert out.get(key) == value, f"{entry_type} dropped {key!r} on round trip"
    assert out["id"] == "rt-probe" and out["type"] == entry_type


def test_declared_fields_win_over_a_stale_extra():
    # An extra never shadows a real field: if a key is both an unknown-at-load
    # key and later becomes a declared field, the declared value is written.
    meta = {"id": "p", "title": "T", "type": "note", "importance": 7}
    entry = entry_from_frontmatter(meta, "b")
    entry.importance = 9
    assert entry.to_frontmatter()["importance"] == 9


def test_update_keeps_undeclared_keys_on_disk(tmp_path):
    from pyrite.config import KBConfig, PyriteConfig, Settings
    from pyrite.services.kb_service import KBService
    from pyrite.storage.database import PyriteDB

    kb = tmp_path / "kb"
    (kb / "backlog").mkdir(parents=True)
    (kb / "backlog" / "item.md").write_text(
        "---\nid: item\ntitle: Item\ntype: backlog_item\nstatus: proposed\n"
        'milestone: "0.13"\ncreated: "2026-09-17"\n---\nbody\n'
    )
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="t", path=kb, kb_type="software")],
        settings=Settings(index_path=tmp_path / "i.db", auto_embed=False),
    )
    svc = KBService(config, PyriteDB(config.settings.index_path))
    svc.index_kb("t") if hasattr(svc, "index_kb") else None
    svc.update_entry("item", "t", status="done")
    text = (kb / "backlog" / "item.md").read_text()
    assert 'milestone: "0.13"' in text or "milestone: '0.13'" in text, text
    assert "2026-09-17" in text, text
    assert "status: done" in text
