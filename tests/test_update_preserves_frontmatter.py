"""Regression tests for #46: `pyrite update` rewriting frontmatter it was not asked to touch.

An update of a single field (`--tags`, `--title`, `-b`) must leave every other
top-level frontmatter key exactly as it was on disk. Before the fix, a
load -> setattr -> save round trip through KBService.update_entry ADDED
`body:` (the whole body re-serialized as a YAML string) and `file_path:`
(an absolute path) to the file, because KBRepository._load_entry injects
those two model internals into the frontmatter dict it hands to
entry_from_frontmatter, and capture_extra_frontmatter then records them as
"unknown frontmatter the class did not emit" and writes them back on save.

Six KB items were corrupted this way in one conductor loop. An item whose
frontmatter grows a `body:` key is silently wrong everywhere that reads
frontmatter, and the file doubles in size on every update.
"""

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB
from pyrite.utils.yaml import load_yaml

# Keys that are model internals, never frontmatter. If any of these appear in
# a saved file's frontmatter, the write path leaked an attribute.
NEVER_IN_FRONTMATTER = ("body", "file_path", "kb_name", "extra_frontmatter")


def _read_frontmatter(path):
    """Parse the YAML frontmatter block of a KB markdown file."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"no frontmatter fence in {path}"
    end = text.index("\n---", 3)
    return load_yaml(text[3:end])


BACKLOG_ITEM = """---
id: sample-backlog-item
type: backlog_item
title: A backlog item with declared and undeclared keys
kind: tech_debt
status: proposed
priority: high
effort: XS
created: "2026-07-03"
milestone: "0.24.2"
github_issue: 46
tags: [testing, quality]
links:
- target: some-other-entry
  relation: related
  kb: swkb
---

## Problem

The body of the entry. It has a `---` divider below to be adversarial.

---

And a second paragraph after it.
"""

NOTE_ENTRY = """---
id: sample-note
type: note
title: A core-type note with an undeclared key
created: "2026-07-03"
custom_field: keep-me
tags: [alpha]
---

Note body.
"""


@pytest.fixture
def swkb_env(tmp_path):
    """A software KB holding one backlog_item and one note, plus a KBService."""
    # The software-kb extension registers `backlog_item`; importing the plugin
    # module is what puts the type in the registry for entry_from_frontmatter.
    pytest.importorskip("pyrite_software_kb.entry_types")
    from pyrite.plugins.registry import PluginRegistry
    from pyrite_software_kb.plugin import SoftwareKBPlugin

    PluginRegistry().register(SoftwareKBPlugin())

    kb_path = tmp_path / "swkb"
    (kb_path / "backlog").mkdir(parents=True)
    (kb_path / "notes").mkdir(parents=True)
    (kb_path / "backlog" / "sample-backlog-item.md").write_text(BACKLOG_ITEM, encoding="utf-8")
    (kb_path / "notes" / "sample-note.md").write_text(NOTE_ENTRY, encoding="utf-8")

    kb = KBConfig(name="swkb", path=kb_path, kb_type="software", description="test software KB")
    config = PyriteConfig(knowledge_bases=[kb], settings=Settings(index_path=tmp_path / "index.db"))
    db = PyriteDB(config.settings.index_path)
    yield {
        "config": config,
        "db": db,
        "service": KBService(config, db),
        "backlog_file": kb_path / "backlog" / "sample-backlog-item.md",
        "note_file": kb_path / "notes" / "sample-note.md",
    }
    db.close()


class TestUpdateLeavesUntouchedFrontmatterAlone:
    """The core of #46: an update of one field changes exactly that field."""

    def test_tags_update_changes_only_tags_on_extension_type(self, swkb_env):
        """`update --tags` on a backlog_item (software-kb extension type).

        This is the exact shape of the reported corruption.
        """
        path = swkb_env["backlog_file"]
        before = _read_frontmatter(path)

        swkb_env["service"].update_entry(
            "sample-backlog-item", "swkb", tags=["testing", "quality", "audit"]
        )

        after = _read_frontmatter(path)
        assert after["tags"] == ["testing", "quality", "audit"]
        # Every other key is byte-for-byte what it was.
        before.pop("tags")
        after.pop("tags")
        assert after == before

    def test_tags_update_never_writes_model_internals(self, swkb_env):
        """`body:`, `file_path:` are attributes of the model, not frontmatter."""
        swkb_env["service"].update_entry("sample-backlog-item", "swkb", tags=["x"])

        after = _read_frontmatter(swkb_env["backlog_file"])
        for key in NEVER_IN_FRONTMATTER:
            assert key not in after, f"{key!r} leaked into frontmatter"

    def test_declared_fields_survive_a_tags_update(self, swkb_env):
        """kind/status/priority/effort are what `pyrite sw backlog` reads."""
        swkb_env["service"].update_entry("sample-backlog-item", "swkb", tags=["x"])

        after = _read_frontmatter(swkb_env["backlog_file"])
        assert after["kind"] == "tech_debt"
        assert after["status"] == "proposed"
        assert after["priority"] == "high"
        assert after["effort"] == "XS"

    def test_undeclared_keys_survive_a_tags_update(self, swkb_env):
        """The PR #35 guarantee: keys the class does not know are preserved."""
        swkb_env["service"].update_entry("sample-backlog-item", "swkb", tags=["x"])

        after = _read_frontmatter(swkb_env["backlog_file"])
        assert after["created"] == "2026-07-03"
        assert after["milestone"] == "0.24.2"
        assert after["github_issue"] == 46

    def test_title_update_changes_only_title(self, swkb_env):
        """`update --title` goes through the same load/save path as --tags."""
        path = swkb_env["backlog_file"]
        before = _read_frontmatter(path)

        swkb_env["service"].update_entry("sample-backlog-item", "swkb", title="A new title")

        after = _read_frontmatter(path)
        assert after["title"] == "A new title"
        before.pop("title")
        after.pop("title")
        assert after == before
        for key in NEVER_IN_FRONTMATTER:
            assert key not in after

    def test_body_update_changes_no_frontmatter_at_all(self, swkb_env):
        """`update -b` rewrites the body; frontmatter must be untouched.

        In particular the new body must NOT appear as a `body:` frontmatter key.
        """
        path = swkb_env["backlog_file"]
        before = _read_frontmatter(path)

        swkb_env["service"].update_entry("sample-backlog-item", "swkb", body="Replaced body.")

        after = _read_frontmatter(path)
        assert after == before
        assert "Replaced body." in path.read_text(encoding="utf-8").split("\n---\n", 1)[1]
        for key in NEVER_IN_FRONTMATTER:
            assert key not in after

    def test_core_type_note_is_protected_too(self, swkb_env):
        """Not an extension-type-only bug: the leak is in the shared load path."""
        path = swkb_env["note_file"]
        before = _read_frontmatter(path)

        swkb_env["service"].update_entry("sample-note", "swkb", tags=["beta"])

        after = _read_frontmatter(path)
        assert after["tags"] == ["beta"]
        assert after["custom_field"] == "keep-me"
        before.pop("tags")
        after.pop("tags")
        assert after == before
        for key in NEVER_IN_FRONTMATTER:
            assert key not in after

    def test_repeated_updates_do_not_grow_the_file(self, swkb_env):
        """The corruption compounded: each update re-embedded the body."""
        path = swkb_env["backlog_file"]
        swkb_env["service"].update_entry("sample-backlog-item", "swkb", tags=["a"])
        after_first = path.stat().st_size
        swkb_env["service"].update_entry("sample-backlog-item", "swkb", tags=["b"])
        after_second = path.stat().st_size

        assert after_second <= after_first + 8


class TestUpdateProducesAMinimalTextDiff:
    """Not just semantically equal -- the same bytes.

    A KB is a git repository. An update that reorders every key and rewrites
    `tags: [a, b]` as a block list produces a 20-line diff for a one-word
    change, which is what made the #46 corruption invisible in review: the
    real damage was buried in reformatting noise.
    """

    def test_tags_update_rewrites_only_the_tags_lines(self, swkb_env):
        path = swkb_env["backlog_file"]
        before = path.read_text(encoding="utf-8").splitlines()

        swkb_env["service"].update_entry(
            "sample-backlog-item", "swkb", tags=["testing", "quality", "audit"]
        )

        after = path.read_text(encoding="utf-8").splitlines()
        changed_before = [l for l in before if l not in after]
        changed_after = [l for l in after if l not in before]
        assert changed_before == ["tags: [testing, quality]"]
        assert changed_after == ["tags: [testing, quality, audit]"]

    def test_key_order_is_preserved(self, swkb_env):
        path = swkb_env["backlog_file"]
        before = list(_read_frontmatter(path).keys())

        swkb_env["service"].update_entry("sample-backlog-item", "swkb", tags=["x"])

        assert list(_read_frontmatter(path).keys()) == before

    def test_title_update_rewrites_only_the_title_line(self, swkb_env):
        path = swkb_env["backlog_file"]
        before = path.read_text(encoding="utf-8").splitlines()

        swkb_env["service"].update_entry("sample-backlog-item", "swkb", title="A new title")

        after = path.read_text(encoding="utf-8").splitlines()
        assert [l for l in before if l not in after] == [
            "title: A backlog item with declared and undeclared keys"
        ]
        assert [l for l in after if l not in before] == ["title: A new title"]


class TestAlwaysWrittenDefaultsStillWork:
    """The narrowing must not undo commit 7783335.

    `importance: 5` and `rank: 0` are written even at their default, because
    the default is a choice a user can make deliberately and dropping it was
    itself a silent-data-loss bug. The #46 fix only stops those keys being
    INVENTED on a file that never had them.
    """

    def test_new_entry_still_writes_default_importance(self):
        from pyrite.models.core_types import NoteEntry

        assert NoteEntry(id="t", title="T").to_frontmatter()["importance"] == 5

    def test_new_backlog_item_still_writes_zero_rank(self):
        pytest.importorskip("pyrite_software_kb.entry_types")
        from pyrite_software_kb.entry_types import BacklogItemEntry

        assert BacklogItemEntry(id="t", title="T", rank=0).to_frontmatter()["rank"] == 0

    def test_a_file_that_has_the_key_keeps_it_through_an_update(self, swkb_env, tmp_path):
        """Explicit `importance: 5` in the file survives a tags update."""
        path = swkb_env["backlog_file"]
        text = path.read_text(encoding="utf-8").replace(
            "effort: XS", "effort: XS\nimportance: 5\nrank: 0"
        )
        path.write_text(text, encoding="utf-8")

        swkb_env["service"].update_entry("sample-backlog-item", "swkb", tags=["x"])

        after = _read_frontmatter(path)
        assert after["importance"] == 5
        assert after["rank"] == 0


class TestLoadDoesNotCaptureInternalsAsExtras:
    """Root cause, tested directly at the layer where it happens."""

    def test_loaded_entry_has_no_internals_in_extra_frontmatter(self, swkb_env):
        from pyrite.storage.repository import KBRepository

        repo = KBRepository(swkb_env["config"].get_kb("swkb"))
        entry = repo.load("sample-backlog-item")

        assert entry is not None
        for key in NEVER_IN_FRONTMATTER:
            assert key not in entry.extra_frontmatter, (
                f"{key!r} captured as undeclared frontmatter; "
                "_load_entry injected a model internal into the meta dict"
            )

    def test_loaded_entry_still_captures_real_extras(self, swkb_env):
        """The fix must not throw away the protection it is narrowing."""
        from pyrite.storage.repository import KBRepository

        repo = KBRepository(swkb_env["config"].get_kb("swkb"))
        entry = repo.load("sample-backlog-item")

        assert entry.extra_frontmatter["milestone"] == "0.24.2"
        assert entry.extra_frontmatter["github_issue"] == 46

    def test_to_frontmatter_of_a_loaded_entry_emits_no_internals(self, swkb_env):
        from pyrite.storage.repository import KBRepository

        repo = KBRepository(swkb_env["config"].get_kb("swkb"))
        entry = repo.load("sample-backlog-item")

        meta = entry.to_frontmatter()
        for key in NEVER_IN_FRONTMATTER:
            assert key not in meta
