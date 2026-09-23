"""An entry id must never name a file outside its KB -- on lookup, not only on write.

`KBRepository.find_file` built `<kb>/<entry_id>.md` with no validation, so the
write-tier MCP tool `kb_delete` with `entry_id: "../victim"` deleted a file
outside the KB, and `repo.load("../secret")` read one. Writes were already
guarded (`_validate_entry_id` + `_contained`); lookups, and so delete, load,
exists and rename's source, were not.
"""

from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.repository import KBRepository

OUTSIDE = "---\ntitle: outside\n---\nprecious\n"


@pytest.fixture
def layout(tmp_path: Path):
    kb = tmp_path / "kb"
    (kb / "notes").mkdir(parents=True)
    victim = tmp_path / "victim.md"
    victim.write_text(OUTSIDE)
    return KBRepository(KBConfig(name="t", path=kb, kb_type="generic")), tmp_path, victim


@pytest.mark.parametrize("bad", ["../victim", "notes/../../victim", "..\\victim", "a\x00b", ""])
def test_find_file_refuses_ids_that_are_not_plain_names(layout, bad):
    repo, _, _ = layout
    assert repo.find_file(bad) is None


def test_find_file_refuses_an_absolute_id(layout):
    repo, tmp, _ = layout
    assert repo.find_file(str(tmp / "victim")) is None


def test_delete_cannot_remove_a_file_outside_the_kb(layout):
    repo, _, victim = layout
    assert not repo.delete("../victim")
    assert victim.exists()


def test_load_cannot_read_a_file_outside_the_kb(layout):
    repo, _, _ = layout
    assert repo.load("../victim") is None


def test_plain_ids_are_still_found(layout):
    repo, _, _ = layout
    (repo.path / "notes" / "real-note.md").write_text("---\nid: real-note\ntitle: R\n---\nb\n")
    assert repo.find_file("real-note") == repo.path / "notes" / "real-note.md"


@pytest.mark.parametrize("pattern", ["*", "real-*", "[r]eal-note", "?eal-note"])
def test_an_id_is_a_name_not_a_glob(layout, pattern):
    """`kb_delete` with entry_id "*" used to delete whichever entry globbed first."""
    repo, _, _ = layout
    (repo.path / "notes" / "real-note.md").write_text("---\nid: real-note\ntitle: R\n---\nb\n")
    assert repo.find_file(pattern) is None
    assert not repo.delete(pattern)
    assert (repo.path / "notes" / "real-note.md").exists()


def test_an_odd_frontmatter_id_is_still_found_by_the_scan(layout):
    """Ids indexed from frontmatter are not slugified; the scan still finds them
    -- inside the KB -- even though they are never turned into a path."""
    repo, _, _ = layout
    f = repo.path / "notes" / "odd.md"
    f.write_text("---\nid: team/odd\ntitle: O\n---\nb\n")
    assert repo.find_file("team/odd") == f


def test_mcp_kb_delete_cannot_remove_a_file_outside_the_kb(tmp_path):
    from pyrite.server.mcp_server import PyriteMCPServer

    kb = tmp_path / "kb"
    kb.mkdir()
    victim = tmp_path / "victim.md"
    victim.write_text(OUTSIDE)
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="t", path=kb, kb_type="generic")],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    result = PyriteMCPServer(config=config, tier="write")._kb_delete(
        {"kb_name": "t", "entry_id": "../victim"}
    )
    assert not result.get("deleted"), result
    assert victim.exists()
