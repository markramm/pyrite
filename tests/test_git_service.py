"""Tests for GitService — subprocess calls mocked."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from pyrite.services.git_service import GitService


class TestParseGithubUrl:
    """Tests for URL parsing (no mocks needed)."""

    def test_https_url(self):
        result = GitService.parse_github_url("https://github.com/org/repo")
        assert result == ("org", "repo")

    def test_https_url_with_git(self):
        result = GitService.parse_github_url("https://github.com/org/repo.git")
        assert result == ("org", "repo")

    def test_ssh_url(self):
        result = GitService.parse_github_url("git@github.com:org/repo.git")
        assert result == ("org", "repo")

    def test_trailing_slash(self):
        result = GitService.parse_github_url("https://github.com/org/repo/")
        assert result == ("org", "repo")

    def test_invalid_url(self):
        result = GitService.parse_github_url("https://gitlab.com/org/repo")
        assert result is None

    def test_incomplete_url(self):
        result = GitService.parse_github_url("https://github.com/org")
        assert result is None


class TestTokenInjection:
    """Tests for _inject_token (no mocks needed)."""

    def test_inject_https(self):
        url = GitService._inject_token("https://github.com/org/repo.git", "mytoken")
        assert url == "https://oauth2:mytoken@github.com/org/repo.git"

    def test_inject_ssh_converted(self):
        url = GitService._inject_token("git@github.com:org/repo.git", "mytoken")
        assert "oauth2:mytoken" in url
        assert "github.com" in url

    def test_no_token(self):
        url = GitService._inject_token("https://github.com/org/repo.git", None)
        assert url == "https://github.com/org/repo.git"


class TestSanitizeOutput:
    """Tests for _sanitize_output."""

    def test_removes_token(self):
        output = GitService._sanitize_output("error with token abc123", "abc123")
        assert "abc123" not in output
        assert "***" in output

    def test_no_token_passthrough(self):
        output = GitService._sanitize_output("some error", None)
        assert output == "some error"


class TestClone:
    """Tests for clone() with subprocess mocked."""

    @patch("pyrite.services.git_service.subprocess.run")
    def test_clone_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        success, msg = GitService.clone("https://github.com/org/repo", Path("/tmp/test"))
        assert success is True
        assert "Cloned" in msg
        mock_run.assert_called_once()

    @patch("pyrite.services.git_service.subprocess.run")
    def test_clone_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="fatal: not found")
        success, msg = GitService.clone("https://github.com/org/repo", Path("/tmp/test"))
        assert success is False
        assert "failed" in msg.lower()

    @patch("pyrite.services.git_service.subprocess.run")
    def test_clone_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=120)
        success, msg = GitService.clone("https://github.com/org/repo", Path("/tmp/test"))
        assert success is False
        assert "timed out" in msg.lower()

    @patch("pyrite.services.git_service.subprocess.run")
    def test_clone_with_depth(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        GitService.clone("https://github.com/org/repo", Path("/tmp/test"), depth=1)
        cmd = mock_run.call_args[0][0]
        assert "--depth" in cmd
        assert "1" in cmd

    @patch("pyrite.services.git_service.subprocess.run")
    def test_clone_full(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        GitService.clone("https://github.com/org/repo", Path("/tmp/test"), depth=None)
        cmd = mock_run.call_args[0][0]
        assert "--depth" not in cmd


class TestPull:
    """Tests for pull() with subprocess mocked."""

    @patch("pyrite.services.git_service.subprocess.run")
    def test_pull_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date")
        success, msg = GitService.pull(Path("/tmp/test"))
        assert success is True

    @patch("pyrite.services.git_service.subprocess.run")
    def test_pull_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="merge conflict")
        success, msg = GitService.pull(Path("/tmp/test"))
        assert success is False


class TestGetters:
    """Tests for git info getters."""

    @patch("pyrite.services.git_service.subprocess.run")
    def test_get_remote_url(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/org/repo.git\n")
        url = GitService.get_remote_url(Path("/tmp/test"))
        assert url == "https://github.com/org/repo.git"

    @patch("pyrite.services.git_service.subprocess.run")
    def test_get_remote_url_none(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        url = GitService.get_remote_url(Path("/tmp/test"))
        assert url is None

    @patch("pyrite.services.git_service.subprocess.run")
    def test_get_current_branch(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="feature-branch\n")
        branch = GitService.get_current_branch(Path("/tmp/test"))
        assert branch == "feature-branch"

    @patch("pyrite.services.git_service.subprocess.run")
    def test_get_head_commit(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123def456\n")
        commit = GitService.get_head_commit(Path("/tmp/test"))
        assert commit == "abc123def456"

    @patch("pyrite.services.git_service.subprocess.run")
    def test_is_git_repo_true(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert GitService.is_git_repo(Path("/tmp/test")) is True

    @patch("pyrite.services.git_service.subprocess.run")
    def test_is_git_repo_false(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128)
        assert GitService.is_git_repo(Path("/tmp/test")) is False


class TestGetFileLog:
    """Tests for get_file_log."""

    @patch("pyrite.services.git_service.subprocess.run")
    def test_get_file_log(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "abc123|Alice|alice@example.com|2025-01-20T10:00:00|Initial commit\n"
                "def456|Bob|bob@example.com|2025-01-21T11:00:00|Update entry\n"
            ),
        )
        log = GitService.get_file_log(Path("/tmp/test"), "actors/test.md")
        assert len(log) == 2
        assert log[0]["hash"] == "abc123"
        assert log[0]["author_name"] == "Alice"
        assert log[1]["message"] == "Update entry"

    @patch("pyrite.services.git_service.subprocess.run")
    def test_get_file_log_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        log = GitService.get_file_log(Path("/tmp/test"), "nonexistent.md")
        assert log == []

    @patch("pyrite.services.git_service.subprocess.run")
    def test_get_file_log_with_since(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        GitService.get_file_log(Path("/tmp/test"), "test.md", since_commit="abc123")
        cmd = mock_run.call_args[0][0]
        assert "abc123..HEAD" in cmd


class TestGetChangedFiles:
    """Tests for get_changed_files."""

    @patch("pyrite.services.git_service.subprocess.run")
    def test_get_changed_files_since_commit(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="actors/alice.md\nevents/2025-01-20.md\n",
        )
        files = GitService.get_changed_files(Path("/tmp/test"), since_commit="abc123")
        assert len(files) == 2
        assert "actors/alice.md" in files

    @patch("pyrite.services.git_service.subprocess.run")
    def test_get_changed_files_all(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="actors/alice.md\n",
        )
        files = GitService.get_changed_files(Path("/tmp/test"))
        assert len(files) == 1
        # Without since_commit, should use ls-files
        cmd = mock_run.call_args[0][0]
        assert "ls-files" in cmd


class TestAddRemote:
    """Tests for add_remote."""

    @patch("pyrite.services.git_service.subprocess.run")
    def test_add_remote_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        success, msg = GitService.add_remote(
            Path("/tmp/test"), "upstream", "https://github.com/org/repo"
        )
        assert success is True

    @patch("pyrite.services.git_service.subprocess.run")
    def test_add_remote_already_exists(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stderr="error: remote upstream already exists."
        )
        success, msg = GitService.add_remote(
            Path("/tmp/test"), "upstream", "https://github.com/org/repo"
        )
        assert success is False
