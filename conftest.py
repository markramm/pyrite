"""Repo-root pytest configuration, shared by tests/ and extensions/*/tests.

Its one job is to cut the suite off from any parent git process.

Under the pre-commit pytest hook the suite runs as a child of `git commit`,
which exports GIT_DIR, GIT_INDEX_FILE and GIT_AUTHOR_* pointing at the real
repository. GIT_DIR beats `cwd`, so a fixture that runs `git config user.name
Test` inside its tmp_path writes to the developer's own .git/config. That is
how this repo authored 39 commits as "Test <test@test.com>", leaked a
`test/alice` branch and worktree, and failed test_kb_commit only under the
hook. Guarding per file (test_worktree_service._clean_git_env) did not hold,
because the next git-using test file did not know to copy it.

This runs at conftest import, before collection, so module- and session-scoped
fixtures are covered too. tests/test_git_env_isolation.py is the canary.
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Identity and repository-location variables git exports to hook subprocesses.
# Everything GIT_* is dropped except the few that only tune behaviour.
_KEEP = frozenset({"GIT_TERMINAL_PROMPT", "GIT_PAGER", "GIT_EDITOR", "GIT_SSH_COMMAND"})


def _isolate_git_environment() -> None:
    for var in [v for v in os.environ if v.startswith("GIT_") and v not in _KEEP]:
        del os.environ[var]

    # Point global/system config at a private file so tests neither read the
    # developer's ~/.gitconfig (signing keys, hooksPath, templates) nor depend
    # on it for an identity. init.defaultBranch is pinned because GitService
    # hardcodes "main" and bare `git init` follows the host's setting.
    config_dir = Path(tempfile.mkdtemp(prefix="pyrite-test-gitconfig-"))
    atexit.register(shutil.rmtree, config_dir, ignore_errors=True)
    global_config = config_dir / "gitconfig"
    global_config.write_text(
        "[user]\n\tname = Pyrite Test Suite\n\temail = test-suite@pyrite.invalid\n"
        "[init]\n\tdefaultBranch = main\n"
        "[commit]\n\tgpgsign = false\n"
        "[tag]\n\tgpgsign = false\n"
    )
    os.environ["GIT_CONFIG_GLOBAL"] = str(global_config)
    os.environ["GIT_CONFIG_SYSTEM"] = os.devnull
    os.environ["GIT_TERMINAL_PROMPT"] = "0"


_isolate_git_environment()


@pytest.fixture(autouse=True)
def _no_auto_embed_unless_marked(request, monkeypatch):
    """Write-time embedding is off for the suite (see tests/test_auto_embed_setting.py).

    Loading the sentence-transformers model costs ~3 s of torch import plus
    network calls to the Hugging Face hub, per process; under `-n auto` every
    worker paid it and the suite thrashed. Tests that exercise embeddings say so:
    `@pytest.mark.embeddings`. Subprocesses spawned by a test inherit the env var.
    """
    if request.node.get_closest_marker("embeddings"):
        return
    from pyrite.services.kb_service import KBService

    def _no_model(self):
        # A test that installed its own (mock) service keeps it; nothing else
        # gets one. Dataclass defaults are frozen into __init__ at class
        # creation, so patching Settings.auto_embed would not reach Settings().
        if getattr(self, "_embedding_checked", False):
            return self._embedding_svc
        self._embedding_checked = True
        return None

    monkeypatch.setattr(KBService, "_get_embedding_svc", _no_model)
    monkeypatch.setenv("PYRITE_AUTO_EMBED", "0")


@pytest.fixture(autouse=True)
def _allow_testclient_host(monkeypatch):
    """Admit TestClient's default Host, ``testserver``, on an auth-disabled app.

    A server with auth disabled answers only the hosts in
    ``pyrite.server.request_guard.LOCAL_HOSTS`` (plus configured names), and
    TestClient addresses every request to ``http://testserver``. Hundreds of
    tests build such an app and say nothing about hosts; this adds that one
    name for them, in tests only. The production default never contains it:
    ``tests/test_request_guard.py`` overrides this fixture with a no-op and
    asserts ``testserver`` gets 421.
    """
    try:
        from pyrite.server import request_guard
    except ImportError:  # server extras not installed
        return
    monkeypatch.setattr(request_guard, "LOCAL_HOSTS", request_guard.LOCAL_HOSTS | {"testserver"})
