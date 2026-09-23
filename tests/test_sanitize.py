"""Tests for pyrite.utils.sanitize."""

import pytest

from pyrite.utils.sanitize import sanitize_filename, unique_path_component


class TestSanitizeFilename:
    def test_normal_id_unchanged(self):
        assert sanitize_filename("hello-world") == "hello-world"

    def test_strips_forward_slash_traversal(self):
        result = sanitize_filename("../../etc/evil")
        assert "/" not in result
        assert ".." not in result

    def test_strips_backslash_traversal(self):
        result = sanitize_filename("..\\..\\etc\\evil")
        assert "\\" not in result
        assert ".." not in result

    def test_simple_parent_ref(self):
        result = sanitize_filename("../secret")
        assert ".." not in result
        assert "/" not in result

    def test_empty_string_returns_fallback(self):
        assert sanitize_filename("") == "_unnamed"

    def test_only_dots_returns_fallback(self):
        assert sanitize_filename("..") == "_unnamed"
        assert sanitize_filename("...") == "_unnamed"

    def test_only_slashes_returns_fallback(self):
        assert sanitize_filename("///") == "_unnamed"

    def test_preserves_hyphens_and_underscores(self):
        assert sanitize_filename("my-entry_v2") == "my-entry_v2"

    def test_preserves_alphanumeric(self):
        assert sanitize_filename("abc123") == "abc123"

    def test_mixed_traversal_and_valid(self):
        result = sanitize_filename("../../valid-name")
        assert "valid-name" in result
        assert ".." not in result

    def test_no_leading_dot_in_result(self):
        result = sanitize_filename(".hidden")
        assert not result.startswith(".")

    def test_absolute_unix_path_becomes_single_component(self):
        """Used as the path-component sanitizer for entry_type and entry.id
        at export/site-renderer joins (#221): pathlib discards the left
        operand when the right is absolute, so an absolute value must never
        reach a `/` join unsanitized."""
        result = sanitize_filename("/etc/passwd")
        assert "/" not in result
        assert result != ""
        assert not result.startswith("/")

    def test_absolute_path_used_as_type_dir_is_relative(self, tmp_path):
        from pathlib import Path

        result = sanitize_filename(str(tmp_path / "outside"))
        joined = Path("/safe/export/dir") / result
        assert joined.is_relative_to("/safe/export/dir")


class TestUniquePathComponent:
    """unique_path_component(raw) -- collision-free deterministic path segment.

    Safe values (sanitize_filename(raw) == raw) keep exactly today's name.
    Unsafe values (sanitizing changed something) get a `-<8 hex>` suffix
    derived from sha256(raw), so distinct raw values that sanitize to the
    same string never collide (#221 redispatch)."""

    def test_safe_value_unchanged(self):
        assert unique_path_component("hello-world") == "hello-world"
        assert unique_path_component("note") == "note"
        assert unique_path_component("a_b") == "a_b"

    def test_unsafe_value_gets_hash_suffix(self):
        import hashlib

        result = unique_path_component("note_")
        suffix = hashlib.sha256(b"note_").hexdigest()[:8]
        assert result == f"note-{suffix}"

    def test_distinct_unsafe_values_that_sanitize_alike_do_not_collide(self):
        raws = ["note_", "note/", "../note", "note..", "note"]
        results = {r: unique_path_component(r) for r in raws}
        assert len(set(results.values())) == len(raws)

    def test_result_has_no_directory_components(self):
        from pathlib import Path

        result = unique_path_component("../../etc/evil")
        assert "/" not in result
        assert not Path(result).is_absolute()

    def test_result_stays_inside_a_join(self, tmp_path):
        from pathlib import Path

        base = tmp_path / "site"
        for raw in ["../../outside", str(tmp_path / "outside"), "a/b", "a_b"]:
            joined = (base / unique_path_component(raw)).resolve()
            assert joined.is_relative_to(base.resolve())

    def test_deterministic(self):
        assert unique_path_component("weird/value") == unique_path_component("weird/value")
