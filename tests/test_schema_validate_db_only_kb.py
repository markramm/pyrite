"""Regression test: `pyrite schema validate <files>` (and `--changed`) must
detect the schema for a KB registered only via `pyrite kb add` (DB-only,
not in config.yaml's knowledge_bases) -- collapse-kb-registry-to-one-
source-of-truth's all_kbs() sweep.

Both schema-detection loops in schema_commands.py's `schema_validate`
iterated `config.knowledge_bases` directly, so a DB-only KB's required-
field validation was silently skipped (schema stayed None, and
validate_entry only runs the required_fields check `if schema:`) even
though `_get_git_changed_md_files` correctly resolved the files via
`config.all_kbs()` on the same code path.
"""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.config import KBConfig, PyriteConfig, Settings

runner = CliRunner()


def _write_kb_yaml_with_required_field(kb_path: Path) -> None:
    (kb_path / "kb.yaml").write_text(
        "name: db-only-kb\nkb_type: generic\ntypes:\n  note:\n    required: [title, owner]\n"
    )


def test_schema_validate_detects_schema_for_db_only_kb(tmp_path):
    kb_path = tmp_path / "db-only-kb"
    kb_path.mkdir()
    _write_kb_yaml_with_required_field(kb_path)

    entry_path = kb_path / "entry.md"
    # Missing the required 'owner' field.
    entry_path.write_text("---\ntype: note\ntitle: Entry\n---\nBody\n")

    # DB-only: not passed to PyriteConfig(knowledge_bases=...). Simulates
    # what config.all_kbs() would return after merge_registered_kbs ran.
    db_only_kb = KBConfig(name="db-only-kb", path=kb_path, kb_type="generic")
    config = PyriteConfig(knowledge_bases=[], settings=Settings(index_path=tmp_path / "index.db"))
    config._db_kb_cache["db-only-kb"] = db_only_kb

    with patch("pyrite.config.load_config", return_value=config):
        result = runner.invoke(app, ["schema", "validate", str(entry_path)])

    assert result.exit_code != 0, (
        f"expected the missing required 'owner' field to fail validation; "
        f"got exit_code=0. Output: {result.output}"
    )
    assert "owner" in result.output, (
        f"expected the required-field error to name 'owner'. Output: {result.output}"
    )
