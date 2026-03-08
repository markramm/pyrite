"""Tests for git blob hash utility."""

import subprocess

from pyrite.utils.hashing import git_blob_hash


class TestGitBlobHash:
    def test_known_vector(self):
        """Verify against a known git blob hash (empty string)."""
        # git hash-object --stdin <<< "" produces the hash for a single newline,
        # but for truly empty content:
        # printf '' | git hash-object --stdin  =>  e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
        assert git_blob_hash(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"

    def test_hello_world(self):
        """Known vector: 'hello world\\n'."""
        # printf 'hello world\n' | git hash-object --stdin
        # => 3b18e512dba79e4c8300dd08aeb37f8e728b8dad
        content = b"hello world\n"
        assert git_blob_hash(content) == "3b18e512dba79e4c8300dd08aeb37f8e728b8dad"

    def test_matches_git_hash_object(self, tmp_path):
        """Compare output with actual git hash-object if available."""
        content = b"The quick brown fox jumps over the lazy dog.\n"
        expected = git_blob_hash(content)

        test_file = tmp_path / "test.txt"
        test_file.write_bytes(content)

        try:
            result = subprocess.run(
                ["git", "hash-object", str(test_file)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                assert expected == result.stdout.strip()
        except FileNotFoundError:
            pass  # git not installed — skip comparison

    def test_binary_content(self):
        """Binary content should hash without error."""
        content = bytes(range(256))
        h = git_blob_hash(content)
        assert len(h) == 40
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self):
        """Same content always produces same hash."""
        content = b"deterministic test"
        assert git_blob_hash(content) == git_blob_hash(content)

    def test_different_content_different_hash(self):
        """Different content produces different hashes."""
        assert git_blob_hash(b"aaa") != git_blob_hash(b"bbb")
