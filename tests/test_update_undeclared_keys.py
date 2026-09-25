"""`update -f key=value` writes a key wherever `create -f` would have put it (#407).

`KBService._update` dropped any key that was neither a model attribute nor
named in the KB's schema -- silently, returning `{"updated": true}` and
leaving the file unchanged. #381/#378 fixed the schema-declared half; this
covers the rest: metadata keys on a generic entry (`foo` on a note) and
undeclared frontmatter keys on a typed entry (`parked_awaiting`/`park_until`
on a task), which `create -f` stores but `update -f` used to discard.

Also covers the two traps the groom named: an update that fails schema
validation must leave the file byte-identical (it did already; this suite
pins it so a refactor of the new merge-into-metadata code can't break it),
and the ADR-0034 truncation-marker keys must still never be persisted now
that undeclared keys are no longer dropped outright.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB
from pyrite.utils.yaml import load_yaml

runner = CliRunner()

NOTE_KB_YAML = """name: notes
kb_type: generic
types:
  note:
    description: A note
"""

TASK_KB_YAML = """name: tasks
kb_type: generic
types:
  task:
    description: A task
"""


def _make_env(tmp_path: Path, kb_name: str, kb_yaml: str) -> tuple[PyriteConfig, Path]:
    kb_path = tmp_path / "kb"
    kb_path.mkdir()
    (kb_path / "kb.yaml").write_text(kb_yaml, encoding="utf-8")
    db_path = tmp_path / "index.db"
    PyriteDB(db_path).close()
    kb = KBConfig(name=kb_name, path=kb_path, kb_type=KBType.GENERIC)
    config = PyriteConfig(knowledge_bases=[kb], settings=Settings(index_path=db_path))
    return config, kb_path


def _invoke(config: PyriteConfig, args: list[str]):
    with patch("pyrite.cli.context.load_config", return_value=config):
        return runner.invoke(app, args)


def _json_payload(result) -> dict:
    text = result.output.strip()
    return json.loads(text[text.index("{") :])


def _entry_id(kb_path: Path) -> str:
    files = list(kb_path.rglob("*.md"))
    assert len(files) == 1, files
    return files[0].stem


def _frontmatter(kb_path: Path) -> dict:
    text = list(kb_path.rglob("*.md"))[0].read_text(encoding="utf-8")
    return load_yaml(text.split("---", 2)[1])


def test_update_field_writes_an_undeclared_metadata_key(tmp_path):
    """`foo` on a note, set at create time, is still writable through update."""
    config, kb_path = _make_env(tmp_path, "notes", NOTE_KB_YAML)
    result = _invoke(
        config,
        ["create", "-k", "notes", "-t", "note", "--title", "N", "-b", "x", "-f", "foo=bar"],
    )
    assert result.exit_code == 0, result.output
    entry_id = _entry_id(kb_path)
    # `note` is a core type (NoteEntry), so an undeclared field lands nested
    # under `metadata:` on create -- this is the shape the #407 repro shows.
    assert _frontmatter(kb_path)["metadata"]["foo"] == "bar"

    result = _invoke(config, ["update", entry_id, "-k", "notes", "-f", "foo=baz"])
    assert result.exit_code == 0, result.output

    assert _frontmatter(kb_path)["metadata"]["foo"] == "baz"


def test_update_field_writes_a_brand_new_undeclared_metadata_key(tmp_path):
    """A key never seen at create time can still be added by update."""
    config, kb_path = _make_env(tmp_path, "notes", NOTE_KB_YAML)
    result = _invoke(config, ["create", "-k", "notes", "-t", "note", "--title", "N", "-b", "x"])
    assert result.exit_code == 0, result.output
    entry_id = _entry_id(kb_path)

    result = _invoke(config, ["update", entry_id, "-k", "notes", "-f", "newkey=v1"])
    assert result.exit_code == 0, result.output

    assert _frontmatter(kb_path)["metadata"]["newkey"] == "v1"


def test_update_field_writes_undeclared_top_level_task_key(tmp_path):
    """`parked_awaiting`/`park_until` land top-level on a task, as create put them."""
    config, kb_path = _make_env(tmp_path, "tasks", TASK_KB_YAML)
    result = _invoke(
        config,
        [
            "create",
            "-k",
            "tasks",
            "-t",
            "task",
            "--title",
            "T",
            "-b",
            "x",
            "-f",
            "parked_awaiting=vote",
        ],
    )
    assert result.exit_code == 0, result.output
    entry_id = _entry_id(kb_path)
    fm = _frontmatter(kb_path)
    assert fm["parked_awaiting"] == "vote"
    assert "metadata" not in fm or "parked_awaiting" not in (fm.get("metadata") or {})

    result = _invoke(config, ["update", entry_id, "-k", "tasks", "-f", "parked_awaiting=other"])
    assert result.exit_code == 0, result.output
    fm = _frontmatter(kb_path)
    assert fm["parked_awaiting"] == "other"
    assert "metadata" not in fm or "parked_awaiting" not in (fm.get("metadata") or {})

    result = _invoke(config, ["update", entry_id, "-k", "tasks", "-f", "park_until=2026-10-08"])
    assert result.exit_code == 0, result.output
    fm = _frontmatter(kb_path)
    assert fm["park_until"] == "2026-10-08"
    assert "metadata" not in fm or "park_until" not in (fm.get("metadata") or {})


@pytest.mark.control(
    reason="the schema refusal (and leaving the file untouched) already worked "
    "before #407; this pins that it still holds now that undeclared keys are "
    "stored instead of dropped"
)
def test_update_rejecting_a_declared_field_leaves_the_file_byte_identical(tmp_path):
    """A schema refusal (enum violation) must not touch the file at all."""
    kb_yaml = """name: statuses
kb_type: generic
types:
  note:
    fields:
      status:
        type: select
        options: [open, done]
validation:
  enforce: true
"""
    config, kb_path = _make_env(tmp_path, "statuses", kb_yaml)
    result = _invoke(
        config,
        ["create", "-k", "statuses", "-t", "note", "--title", "N", "-b", "x", "-f", "status=open"],
    )
    assert result.exit_code == 0, result.output
    entry_id = _entry_id(kb_path)
    path = list(kb_path.rglob("*.md"))[0]
    before = path.read_text(encoding="utf-8")

    result = _invoke(config, ["update", entry_id, "-k", "statuses", "-f", "status=bogus"])
    assert result.exit_code != 0
    payload = _json_payload(result)
    assert payload.get("error_code") == "SCHEMA_VIOLATION", payload

    after = path.read_text(encoding="utf-8")
    assert after == before


@pytest.mark.control(
    reason="the markers were dropped before #407 too, as a side effect of the "
    "bug this issue closes (hasattr -> False -> continue); this pins that they "
    "stay dropped now that the strip is deliberate rather than accidental"
)
def test_update_does_not_persist_truncation_marker_keys(tmp_path):
    """`body_truncated=false` (and the other ADR-0034 marker keys) never land in the file."""
    config, kb_path = _make_env(tmp_path, "notes", NOTE_KB_YAML)
    result = _invoke(config, ["create", "-k", "notes", "-t", "note", "--title", "N", "-b", "x"])
    assert result.exit_code == 0, result.output
    entry_id = _entry_id(kb_path)

    result = _invoke(config, ["update", entry_id, "-k", "notes", "-f", "body_truncated=false"])
    assert result.exit_code == 0, result.output

    fm = _frontmatter(kb_path)
    nested = fm.get("metadata") or {}
    for marker in ("body_truncated", "body_length", "body_offset", "body_chunk_size"):
        assert marker not in fm, fm
        assert marker not in nested, nested
