"""Repo endpoints must not leak git stderr or absolute server paths.

CodeQL py/stack-trace-exposure alerts #51 (subscribe), #52 (fork), #53 (pr).
The reproduced leak was a 400 body reading::

    Clone failed: Cloning into '/Users/<user>/.pyrite/repos/owner/repo'...
    remote: Repository not found.
    fatal: repository 'https://github.com/owner/repo/' not found

— raw git stderr plus the server's absolute filesystem layout, handed to a
write-tier caller. The token was already stripped; the paths were not.

Every git call here is stubbed with *recorded* stderr shapes (captured from
real git 2.x on 2026-09-18); nothing in this file clones a real repository or
writes outside ``tmp_path``.
"""

import logging
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyrite.config import AuthConfig, PyriteConfig, Settings
from pyrite.services.git_service import GitService
from pyrite.services.repo_service import RepoService
from pyrite.storage.database import PyriteDB

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")

from pyrite.server.api import get_repo_service  # noqa: E402

# --- Recorded git stderr shapes -------------------------------------------
# Captured verbatim from git; the leading "Cloning into '<abs path>'" line is
# what git always emits first, and is the path disclosure itself.

STDERR_REPO_NOT_FOUND = (
    "Cloning into '{dest}'...\n"
    "remote: Repository not found.\n"
    "fatal: repository 'https://github.com/owner/repo/' not found\n"
)

STDERR_AUTH_FAILED = (
    "Cloning into '{dest}'...\n"
    "remote: Invalid username or token. Password authentication is not supported.\n"
    "fatal: Authentication failed for 'https://github.com/owner/repo/'\n"
)

STDERR_AUTH_NO_USERNAME = (
    "Cloning into '{dest}'...\n"
    "fatal: could not read Username for 'https://github.com': terminal prompts disabled\n"
)

STDERR_BRANCH_NOT_FOUND = (
    "Cloning into '{dest}'...\n"
    "warning: Could not find remote branch no-such-branch to clone.\n"
    "fatal: Remote branch no-such-branch not found in upstream origin\n"
)


def _fake_clone_run(stderr_template: str):
    """A subprocess.run stub that fails a `git clone` with `stderr_template`,
    filling in whatever destination path the real call passed."""

    def _run(cmd, *args, **kwargs):
        dest = cmd[-1]
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 128
        result.stdout = ""
        result.stderr = stderr_template.format(dest=dest)
        return result

    return _run


@pytest.fixture
def workspace(tmp_path):
    """A workspace root under tmp_path — never ``~/.pyrite``."""
    path = tmp_path / "workspace"
    path.mkdir()
    return path


@pytest.fixture
def repo_service(tmp_path, workspace):
    db = PyriteDB(tmp_path / "index.db")
    config = PyriteConfig(
        settings=Settings(index_path=tmp_path / "index.db", workspace_path=workspace)
    )
    yield RepoService(config, db)
    db.close()


class TestSanitiser:
    """Criterion 1: a path-redacting step additive to _sanitize_output."""

    def test_absolute_path_is_replaced_with_placeholder(self, tmp_path):
        dest = tmp_path / "owner" / "repo"
        raw = STDERR_REPO_NOT_FOUND.format(dest=dest)

        safe = GitService.sanitize_error(raw, token=None)

        assert str(tmp_path) not in safe
        assert str(dest) not in safe
        assert "Cloning into" not in safe

    def test_token_redaction_is_preserved(self, tmp_path):
        raw = f"Cloning into '{tmp_path}/o/r'...\nfatal: bad token ghp_secret123\n"

        safe = GitService.sanitize_error(raw, token="ghp_secret123")

        assert "ghp_secret123" not in safe
        assert str(tmp_path) not in safe

    def test_windows_style_absolute_path_is_replaced(self):
        raw = "Cloning into 'C:\\Users\\alice\\.pyrite\\repos\\owner\\repo'...\nfatal: nope\n"

        safe = GitService.sanitize_error(raw, token=None)

        assert "C:\\Users\\alice" not in safe

    def test_sanitize_output_still_exists_and_redacts_tokens(self):
        assert GitService._sanitize_output("err ghp_x", "ghp_x") == "err ***"


class TestErrorClassification:
    """Criterion 3: three actionable failures map to three stable codes."""

    @pytest.mark.parametrize(
        ("template", "expected_code"),
        [
            (STDERR_REPO_NOT_FOUND, "REPO_NOT_FOUND"),
            (STDERR_AUTH_FAILED, "AUTH_REQUIRED"),
            (STDERR_AUTH_NO_USERNAME, "AUTH_REQUIRED"),
            (STDERR_BRANCH_NOT_FOUND, "BRANCH_NOT_FOUND"),
        ],
    )
    def test_classify(self, tmp_path, template, expected_code):
        raw = template.format(dest=tmp_path / "owner" / "repo")

        code, message = GitService.classify_git_error(raw, token=None)

        assert code == expected_code
        assert str(tmp_path) not in message
        assert "Cloning into" not in message

    def test_codes_are_distinct(self, tmp_path):
        codes = {
            GitService.classify_git_error(t.format(dest=tmp_path / "o" / "r"), None)[0]
            for t in (STDERR_REPO_NOT_FOUND, STDERR_AUTH_FAILED, STDERR_BRANCH_NOT_FOUND)
        }
        assert len(codes) == 3

    def test_unknown_stderr_falls_back_without_leaking(self, tmp_path):
        raw = f"Cloning into '{tmp_path}/o/r'...\nfatal: something entirely new\n"

        code, message = GitService.classify_git_error(raw, token=None)

        assert code == "CLONE_FAILED"
        assert str(tmp_path) not in message


class TestCloneLogsFullStderr:
    """Criterion 4: the operator still gets everything the body omits."""

    def test_clone_logs_raw_stderr_at_warning(self, tmp_path, caplog):
        dest = tmp_path / "owner" / "repo"
        raw = STDERR_REPO_NOT_FOUND.format(dest=dest)

        with (
            patch("subprocess.run", _fake_clone_run(STDERR_REPO_NOT_FOUND)),
            caplog.at_level(logging.WARNING, logger="pyrite.services.git_service"),
        ):
            success, message = GitService.clone(
                "https://github.com/owner/repo", dest, branch="main"
            )

        assert success is False
        assert str(dest) not in message
        assert "Cloning into" not in message

        logged = "\n".join(r.getMessage() for r in caplog.records)
        assert "Repository not found" in logged
        assert str(dest) in logged, "the operator must still see the real path"
        assert raw.strip().splitlines()[-1] in logged


class TestSubscribeEndpointDisclosure:
    """Criterion 2 + 3, end to end through the REST endpoint."""

    @pytest.fixture
    def client_factory(self, make_client, workspace, tmp_path):
        def _make(service):
            client, _, _ = make_client(
                auth=AuthConfig(enabled=True, allow_registration=True),
                dependency_overrides={get_repo_service: lambda: service},
                register_user=("testuser", "password123"),
            )
            return client

        return _make

    def test_subscribe_nonexistent_repo_leaks_no_paths(
        self, client_factory, repo_service, workspace, tmp_path
    ):
        client = client_factory(repo_service)

        with patch("subprocess.run", _fake_clone_run(STDERR_REPO_NOT_FOUND)):
            r = client.post(
                "/api/repos/subscribe",
                json={"remote_url": "https://github.com/owner/repo"},
            )

        assert r.status_code == 400
        detail = r.json()["detail"]
        body = r.text

        # The exact regression string from the CodeQL report.
        assert "Cloning into" not in body
        assert str(workspace) not in body
        assert str(tmp_path) not in body
        assert str(Path.home()) not in body
        assert detail["code"] == "REPO_NOT_FOUND"
        # ...but the caller can still act on it.
        assert "not found" in detail["message"].lower()

    @pytest.mark.parametrize(
        ("template", "expected_code"),
        [
            (STDERR_REPO_NOT_FOUND, "REPO_NOT_FOUND"),
            (STDERR_AUTH_FAILED, "AUTH_REQUIRED"),
            (STDERR_BRANCH_NOT_FOUND, "BRANCH_NOT_FOUND"),
        ],
    )
    def test_subscribe_reports_distinct_codes(
        self, client_factory, repo_service, tmp_path, template, expected_code
    ):
        client = client_factory(repo_service)

        with patch("subprocess.run", _fake_clone_run(template)):
            r = client.post(
                "/api/repos/subscribe",
                json={"remote_url": "https://github.com/owner/repo"},
            )

        assert r.status_code == 400
        assert r.json()["detail"]["code"] == expected_code
        assert str(tmp_path) not in r.text


class TestForkAndPRDisclosure:
    """Criterion 5: fork (#52) and pr (#53) route errors through the same
    sanitiser."""

    @pytest.fixture
    def client_factory(self, make_client):
        def _make(service):
            client, _, _ = make_client(
                auth=AuthConfig(enabled=True, allow_registration=True),
                dependency_overrides={get_repo_service: lambda: service},
                register_user=("testuser", "password123"),
            )
            return client

        return _make

    def test_fork_error_is_sanitised(self, client_factory, tmp_path):
        leaky = f"Cloning into '{tmp_path}/owner/repo'...\nfatal: repository not found\n"
        svc = MagicMock(spec=RepoService)
        svc._github_token = "ghp_test"
        svc.fork_and_subscribe.return_value = {"success": False, "error": leaky}
        client = client_factory(svc)

        r = client.post("/api/repos/fork", json={"remote_url": "https://github.com/owner/repo"})

        assert r.status_code == 400
        assert str(tmp_path) not in r.text
        assert "Cloning into" not in r.text

    def test_pr_error_is_sanitised(self, client_factory, tmp_path):
        leaky = f"fatal: cannot open '{tmp_path}/owner/repo/.git/config'\n"
        svc = MagicMock(spec=RepoService)
        svc._github_token = "ghp_test"
        svc.create_pr.return_value = {"success": False, "error": leaky}
        client = client_factory(svc)

        r = client.post("/api/repos/owner/repo/pr", json={"title": "T", "body": "B"})

        assert r.status_code == 400
        assert str(tmp_path) not in r.text
