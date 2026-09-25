"""The `/repos/{name}` routes apply per-KB authorization to a repo's KBs.

A repository is a container of KBs. The routes that name one were guarded by
the global `write` tier only, so any write-tier user could read the status of
a repo holding a private KB (its KB names, entry count and contributors), sync
it, open a pull request from it, or unsubscribe it -- which removes its KBs
from the instance for everyone. Per-KB grants and default roles never entered
into it.

Now, for every KB the repository contains:

- ``GET /repos/{name}`` requires read;
- ``POST /repos/{name}/sync`` and ``POST /repos/{name}/pr`` require write;
- ``DELETE /repos/{name}`` requires admin, the tier ``DELETE /api/kbs/{name}``
  requires, because unsubscribing removes those KBs.

A caller who may not read one of the KBs gets exactly the answer a repository
that does not exist gets on that route; its existence is private too. A caller
who may read them but lacks the tier gets 403.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db, get_repo_service
from pyrite.services.auth_service import AuthService
from pyrite.services.repo_service import RepoService
from pyrite.storage.database import PyriteDB
from tests.auth_seed import seed_user

PUBLIC, PRIVATE = "public-kb", "private-kb"
SECRET_REPO, OPEN_REPO, MISSING_REPO = "owner/secret", "owner/open", "owner/no-such-repo"


@pytest.fixture
def env(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pyrite.config.CONFIG_FILE", tmp_path / "config.yaml")
    for name in (PUBLIC, PRIVATE):
        (tmp_path / name).mkdir()
    config = PyriteConfig(
        knowledge_bases=[
            KBConfig(name=PUBLIC, path=tmp_path / PUBLIC, kb_type="generic", default_role="read"),
            KBConfig(name=PRIVATE, path=tmp_path / PRIVATE, kb_type="generic", default_role="none"),
        ],
        settings=Settings(
            index_path=tmp_path / "index.db",
            workspace_path=tmp_path / "workspace",
            auth=AuthConfig(enabled=True, allow_registration=True, anonymous_tier="read"),
        ),
    )
    app = create_app(config=config)
    db = PyriteDB(config.settings.index_path)
    app.dependency_overrides[get_config] = lambda: config
    app.dependency_overrides[get_db] = lambda: db

    def repo_service_with_token():
        # A connected GitHub account, so /pr gets past its token check and the
        # repo lookup is what decides the answer.
        svc = RepoService(config, db)
        svc._github_token = "gh-test-token"
        return svc

    app.dependency_overrides[get_repo_service] = repo_service_with_token

    for repo_name, kb_name in ((SECRET_REPO, PRIVATE), (OPEN_REPO, PUBLIC)):
        repo = db.register_repo(repo_name, str(tmp_path / "workspace" / repo_name))
        db.register_kb(kb_name, "generic", str(tmp_path / kb_name))
        db.link_kb_to_repo(kb_name, repo["id"], "")

    auth = AuthService(db, config.settings.auth)

    def client_for(username, *, role="write", grant=None):
        c = TestClient(app)
        user = seed_user(db, username, "password123", role=role)
        if grant:
            auth.grant_kb_permission(user["id"], PRIVATE, grant, user["id"])
        c.cookies.set(
            "pyrite_session",
            AuthService(db, config.settings.auth).login(username, "password123")[1],
        )
        return c

    clients = {"admin": client_for("admin-user", role="admin")}  # seeded as admin
    clients["peer"] = client_for("peer")  # global write, no grant on PRIVATE
    clients["reader"] = client_for("reader", grant="read")
    clients["writer"] = client_for("writer", grant="write")
    clients["kb_admin"] = client_for("kb-admin", grant="admin")
    try:
        yield {**clients, "db": db}
    finally:
        db.close()
        state_db = getattr(app.state, "pyrite_db", None)
        if state_db is not None and state_db is not db:
            state_db.close()


def _call(client, route: str, repo: str):
    if route == "get":
        return client.get(f"/api/repos/{repo}")
    if route == "sync":
        return client.post(f"/api/repos/{repo}/sync")
    if route == "pr":
        return client.post(f"/api/repos/{repo}/pr", json={"title": "t"})
    if route == "delete":
        return client.delete(f"/api/repos/{repo}")
    raise AssertionError(route)


def _normalised(resp, repo: str):
    return resp.status_code, resp.text.replace(repo, "<repo>")


ROUTES = ["get", "sync", "pr", "delete"]


@pytest.mark.parametrize("route", ROUTES)
def test_unreadable_repo_answers_exactly_as_a_nonexistent_one(env, route):
    hidden = _call(env["peer"], route, SECRET_REPO)
    missing = _call(env["peer"], route, MISSING_REPO)
    assert _normalised(hidden, SECRET_REPO) == _normalised(missing, MISSING_REPO)
    assert PRIVATE not in hidden.text
    # Nothing was removed on the way.
    assert env["db"].get_repo(name=SECRET_REPO) is not None


def test_reader_can_read_the_repo(env):
    r = _call(env["reader"], "get", SECRET_REPO)
    assert r.status_code == 200, r.text
    assert r.json()["kb_names"] == [PRIVATE]


@pytest.mark.parametrize("route", ["sync", "pr", "delete"])
def test_reader_cannot_change_the_repo(env, route):
    r = _call(env["reader"], route, SECRET_REPO)
    assert r.status_code == 403, r.text
    assert env["db"].get_repo(name=SECRET_REPO) is not None


@pytest.mark.parametrize("route", ["sync", "pr"])
def test_writer_gets_past_the_guard_for_sync_and_pr(env, route):
    r = _call(env["writer"], route, SECRET_REPO)
    # sync: 200 (the clone is not on disk, reported per repo);
    # pr: 400 from the service ("not a fork") -- either way, not refused.
    assert r.status_code not in (403, 404), r.text
    if route == "pr":
        assert "not a fork" in r.text


def test_writer_cannot_unsubscribe_it_needs_admin_on_the_kbs(env):
    r = _call(env["writer"], "delete", SECRET_REPO)
    assert r.status_code == 403, r.text
    assert env["db"].get_repo(name=SECRET_REPO) is not None


def test_kb_admin_can_unsubscribe(env):
    r = _call(env["kb_admin"], "delete", SECRET_REPO)
    assert r.status_code == 200, r.text
    assert env["db"].get_repo(name=SECRET_REPO) is None


def test_public_repo_is_readable_by_a_peer(env):
    r = _call(env["peer"], "get", OPEN_REPO)
    assert r.status_code == 200, r.text
    assert r.json()["kb_names"] == [PUBLIC]


def test_global_admin_is_unscoped(env):
    r = _call(env["admin"], "get", SECRET_REPO)
    assert r.status_code == 200, r.text
    assert r.json()["kb_names"] == [PRIVATE]


def _listed(client) -> set[str]:
    r = client.get("/api/repos")
    assert r.status_code == 200, r.text
    return {repo["name"] for repo in r.json()["repos"]}


def test_list_omits_a_repo_whose_kbs_the_caller_cannot_read(env):
    """`GET /api/repos` answers as if the repository did not exist."""
    r = env["peer"].get("/api/repos")
    assert _listed(env["peer"]) == {OPEN_REPO}
    assert SECRET_REPO not in r.text
    assert PRIVATE not in r.text


def test_list_includes_it_for_a_grantee_and_a_global_admin(env):
    assert _listed(env["reader"]) == {SECRET_REPO, OPEN_REPO}
    assert _listed(env["admin"]) == {SECRET_REPO, OPEN_REPO}
