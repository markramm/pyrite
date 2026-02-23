"""Tests for pyrite.utils.yaml round-trip YAML utilities."""

from pyrite.utils.yaml import dump_yaml, dump_yaml_file, load_yaml, load_yaml_file


class TestLoadYaml:
    def test_load_simple(self):
        text = "title: Hello\ntags: [a, b]"
        result = load_yaml(text)
        assert result["title"] == "Hello"
        assert result["tags"] == ["a", "b"]

    def test_load_empty(self):
        result = load_yaml("")
        assert not result or result == {}

    def test_load_preserves_order(self):
        text = "z_field: 1\na_field: 2\nm_field: 3"
        result = load_yaml(text)
        keys = list(result.keys())
        assert keys == ["z_field", "a_field", "m_field"]

    def test_load_nested(self):
        text = "parent:\n  child: value\n  list:\n  - a\n  - b"
        result = load_yaml(text)
        assert result["parent"]["child"] == "value"
        assert result["parent"]["list"] == ["a", "b"]

    def test_load_result_is_dict_compatible(self):
        """CommentedMap should work like a dict."""
        text = "a: 1\nb: 2"
        result = load_yaml(text)
        # Standard dict operations
        assert "a" in result
        assert result.get("c", "default") == "default"
        assert len(result) == 2
        assert list(result.items()) == [("a", 1), ("b", 2)]


class TestDumpYaml:
    def test_dump_simple(self):
        data = {"title": "Hello", "tags": ["a", "b"]}
        result = dump_yaml(data)
        assert "title: Hello" in result
        assert "tags:" in result

    def test_dump_no_sort_keys(self):
        """Keys should preserve insertion order, not be sorted."""
        data = {"z": 1, "a": 2, "m": 3}
        result = dump_yaml(data)
        lines = [l for l in result.split("\n") if l.strip()]
        assert lines[0].startswith("z:")
        assert lines[1].startswith("a:")
        assert lines[2].startswith("m:")

    def test_dump_returns_string(self):
        data = {"key": "value"}
        result = dump_yaml(data)
        assert isinstance(result, str)

    def test_dump_no_trailing_newline(self):
        """dump_yaml should strip trailing newline."""
        data = {"key": "value"}
        result = dump_yaml(data)
        assert not result.endswith("\n")


class TestRoundTrip:
    def test_round_trip_preserves_content(self):
        """Load then dump should produce semantically identical output."""
        original = "title: Test Entry\ntype: note\ntags:\n- alpha\n- beta\ndate: '2024-01-15'"
        data = load_yaml(original)
        result = dump_yaml(data)
        reloaded = load_yaml(result)
        assert reloaded["title"] == "Test Entry"
        assert reloaded["type"] == "note"
        assert reloaded["tags"] == ["alpha", "beta"]

    def test_round_trip_preserves_quoting(self):
        """Quoted strings should stay quoted."""
        original = "date: '2024-01-15'\ntitle: \"Hello World\""
        data = load_yaml(original)
        result = dump_yaml(data)
        assert "'2024-01-15'" in result

    def test_round_trip_preserves_comments(self):
        """Comments should survive round-trip."""
        original = "# This is a comment\ntitle: Test\n# Another comment\ntags: []"
        data = load_yaml(original)
        result = dump_yaml(data)
        assert "# This is a comment" in result

    def test_round_trip_single_field_change(self):
        """Changing one field should only affect that field in output."""
        original = "title: Original\ntype: note\ntags:\n- alpha"
        data = load_yaml(original)
        data["title"] = "Changed"
        result = dump_yaml(data)
        assert "title: Changed" in result
        assert "type: note" in result
        assert "- alpha" in result

    def test_round_trip_preserves_key_order(self):
        """Key order should be preserved through round-trip."""
        original = "z_last: 1\na_first: 2\nm_middle: 3"
        data = load_yaml(original)
        result = dump_yaml(data)
        lines = [l for l in result.split("\n") if l.strip()]
        assert lines[0].startswith("z_last:")
        assert lines[1].startswith("a_first:")
        assert lines[2].startswith("m_middle:")


class TestFileOperations:
    def test_file_round_trip(self, tmp_path):
        original = {"title": "Test", "tags": ["a", "b"]}
        path = tmp_path / "test.yaml"
        dump_yaml_file(original, path)
        loaded = load_yaml_file(path)
        assert loaded["title"] == "Test"
        assert loaded["tags"] == ["a", "b"]

    def test_load_yaml_file_empty(self, tmp_path):
        path = tmp_path / "empty.yaml"
        path.write_text("")
        result = load_yaml_file(path)
        assert not result or result == {}

    def test_dump_yaml_file_creates_file(self, tmp_path):
        path = tmp_path / "new.yaml"
        dump_yaml_file({"key": "value"}, path)
        assert path.exists()
        content = path.read_text()
        assert "key: value" in content

    def test_file_round_trip_with_path_object(self, tmp_path):
        """Should work with both str and Path objects."""
        data = {"x": 1}
        path = tmp_path / "test.yaml"
        dump_yaml_file(data, str(path))
        loaded = load_yaml_file(str(path))
        assert loaded["x"] == 1
