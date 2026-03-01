"""Tests for Phase 7 collaboration ORM models and DB operations."""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBType
from pyrite.storage.database import PyriteDB


@pytest.fixture
def db():
    """Create a temporary database with collaboration tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = PyriteDB(db_path)
        yield db
        db.close()


class TestUserModel:
    """Tests for User table operations."""

    def test_local_user_exists(self, db):
        """Sentinel 'local' user is created by migration."""
        user = db.get_local_user()
        assert user["github_login"] == "local"
        assert user["github_id"] == 0
        assert user["display_name"] == "Local User"

    def test_upsert_user_creates(self, db):
        """upsert_user creates a new user."""
        user = db.upsert_user("octocat", 123, "The Octocat", "", "octocat@github.com")
        assert user["github_login"] == "octocat"
        assert user["github_id"] == 123
        assert user["display_name"] == "The Octocat"
        assert user["email"] == "octocat@github.com"

    def test_upsert_user_updates(self, db):
        """upsert_user updates existing user."""
        db.upsert_user("octocat", 123, "Octo Cat")
        updated = db.upsert_user("octocat-new", 123, "New Name")
        assert updated["github_login"] == "octocat-new"
        assert updated["display_name"] == "New Name"

    def test_get_user_by_login(self, db):
        """get_user retrieves by login."""
        db.upsert_user("alice", 100, "Alice")
        user = db.get_user(github_login="alice")
        assert user is not None
        assert user["github_id"] == 100

    def test_get_user_by_id(self, db):
        """get_user retrieves by GitHub ID."""
        db.upsert_user("bob", 200, "Bob")
        user = db.get_user(github_id=200)
        assert user is not None
        assert user["github_login"] == "bob"

    def test_get_user_not_found(self, db):
        """get_user returns None for nonexistent user."""
        assert db.get_user(github_login="nobody") is None
        assert db.get_user(github_id=99999) is None

    def test_get_user_no_args(self, db):
        """get_user returns None when no args given."""
        assert db.get_user() is None


class TestRepoModel:
    """Tests for Repo table operations."""

    def test_register_repo(self, db):
        """register_repo creates a new repo."""
        repo = db.register_repo("org/test-kb", "/tmp/test")
        assert repo["name"] == "org/test-kb"
        assert repo["local_path"] == "/tmp/test"
        assert repo["visibility"] == "public"
        assert repo["default_branch"] == "main"
        assert repo["is_fork"] == 0

    def test_register_repo_with_remote(self, db):
        """register_repo stores remote URL and owner."""
        repo = db.register_repo(
            "org/research",
            "/tmp/research",
            remote_url="https://github.com/org/research",
            owner="org",
        )
        assert repo["remote_url"] == "https://github.com/org/research"
        assert repo["owner"] == "org"

    def test_register_repo_upsert(self, db):
        """register_repo updates existing repo."""
        db.register_repo("org/kb", "/tmp/old")
        updated = db.register_repo("org/kb", "/tmp/new")
        assert updated["local_path"] == "/tmp/new"

    def test_get_repo_by_name(self, db):
        """get_repo retrieves by name."""
        db.register_repo("org/kb", "/tmp/test")
        repo = db.get_repo(name="org/kb")
        assert repo is not None
        assert repo["local_path"] == "/tmp/test"

    def test_get_repo_by_id(self, db):
        """get_repo retrieves by ID."""
        created = db.register_repo("org/kb", "/tmp/test")
        repo = db.get_repo(repo_id=created["id"])
        assert repo is not None
        assert repo["name"] == "org/kb"

    def test_get_repo_not_found(self, db):
        """get_repo returns None for nonexistent repo."""
        assert db.get_repo(name="nonexistent") is None

    def test_list_repos(self, db):
        """list_repos returns all repos."""
        db.register_repo("a/first", "/tmp/a")
        db.register_repo("b/second", "/tmp/b")
        repos = db.list_repos()
        assert len(repos) == 2
        names = {r["name"] for r in repos}
        assert "a/first" in names
        assert "b/second" in names

    def test_delete_repo(self, db):
        """delete_repo removes a repo."""
        db.register_repo("org/kb", "/tmp/test")
        assert db.delete_repo("org/kb") is True
        assert db.get_repo(name="org/kb") is None

    def test_delete_repo_not_found(self, db):
        """delete_repo returns False for nonexistent repo."""
        assert db.delete_repo("nonexistent") is False

    def test_update_repo_synced(self, db):
        """update_repo_synced records commit hash and timestamp."""
        db.register_repo("org/kb", "/tmp/test")
        db.update_repo_synced("org/kb", "abc123def456")
        repo = db.get_repo(name="org/kb")
        assert repo["last_synced_commit"] == "abc123def456"
        assert repo["last_synced"] is not None

    def test_fork_tracking(self, db):
        """Repos can track upstream via upstream_repo_id."""
        upstream = db.register_repo("org/upstream", "/tmp/up")
        fork = db.register_repo(
            "me/fork",
            "/tmp/fork",
            upstream_repo_id=upstream["id"],
            is_fork=True,
        )
        assert fork["upstream_repo_id"] == upstream["id"]
        assert fork["is_fork"] == 1


class TestWorkspaceRepoModel:
    """Tests for WorkspaceRepo operations."""

    def test_add_workspace_repo(self, db):
        """add_workspace_repo creates a membership."""
        user = db.upsert_user("alice", 100, "Alice")
        repo = db.register_repo("org/kb", "/tmp/test")
        db.add_workspace_repo(user["id"], repo["id"], "subscriber")

        repos = db.get_workspace_repos(user["id"])
        assert len(repos) == 1
        assert repos[0]["name"] == "org/kb"
        assert repos[0]["role"] == "subscriber"

    def test_add_workspace_repo_idempotent(self, db):
        """Adding same workspace repo twice doesn't duplicate."""
        user = db.upsert_user("alice", 100, "Alice")
        repo = db.register_repo("org/kb", "/tmp/test")
        db.add_workspace_repo(user["id"], repo["id"])
        db.add_workspace_repo(user["id"], repo["id"])  # Should not raise

        repos = db.get_workspace_repos(user["id"])
        assert len(repos) == 1

    def test_remove_workspace_repo(self, db):
        """remove_workspace_repo deletes membership."""
        user = db.upsert_user("alice", 100, "Alice")
        repo = db.register_repo("org/kb", "/tmp/test")
        db.add_workspace_repo(user["id"], repo["id"])

        assert db.remove_workspace_repo(user["id"], repo["id"]) is True
        assert db.get_workspace_repos(user["id"]) == []

    def test_multiple_repos_per_user(self, db):
        """User can have multiple repos in workspace."""
        user = db.upsert_user("alice", 100, "Alice")
        r1 = db.register_repo("org/first", "/tmp/a")
        r2 = db.register_repo("org/second", "/tmp/b")
        db.add_workspace_repo(user["id"], r1["id"], "owner")
        db.add_workspace_repo(user["id"], r2["id"], "subscriber")

        repos = db.get_workspace_repos(user["id"])
        assert len(repos) == 2


class TestEntryVersionModel:
    """Tests for EntryVersion operations."""

    def test_upsert_entry_version(self, db):
        """upsert_entry_version creates a version record."""
        db.register_kb("test-kb", KBType.RESEARCH, "/tmp/test")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Test",
                "body": "",
            }
        )

        db.upsert_entry_version(
            entry_id="entry-1",
            kb_name="test-kb",
            commit_hash="abc123def456789012345678901234567890abcd",
            author_name="Alice",
            author_email="alice@example.com",
            commit_date="2025-01-20T10:00:00",
            message="Add actor entry",
            change_type="created",
        )

        versions = db.get_entry_versions("entry-1", "test-kb")
        assert len(versions) == 1
        assert versions[0]["author_name"] == "Alice"
        assert versions[0]["change_type"] == "created"

    def test_multiple_versions(self, db):
        """Multiple versions are stored for an entry."""
        db.register_kb("test-kb", KBType.RESEARCH, "/tmp/test")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Test",
                "body": "",
            }
        )

        for i in range(3):
            db.upsert_entry_version(
                entry_id="entry-1",
                kb_name="test-kb",
                commit_hash=f"{'a' * 39}{i}",
                author_name=f"Author {i}",
                author_email=f"author{i}@example.com",
                commit_date=f"2025-01-{20 + i:02d}T10:00:00",
                message=f"Commit {i}",
                change_type="modified" if i > 0 else "created",
            )

        versions = db.get_entry_versions("entry-1", "test-kb")
        assert len(versions) == 3
        # Ordered by commit_date DESC
        assert versions[0]["commit_date"] == "2025-01-22T10:00:00"

    def test_entry_versions_empty(self, db):
        """get_entry_versions returns empty list for no versions."""
        versions = db.get_entry_versions("nonexistent", "test-kb")
        assert versions == []

    def test_get_contributors(self, db):
        """get_contributors aggregates from entry_version."""
        db.register_kb("test-kb", KBType.RESEARCH, "/tmp/test")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Test",
                "body": "",
            }
        )

        # Alice makes 2 commits, Bob makes 1
        for i, (name, email) in enumerate(
            [
                ("Alice", "alice@example.com"),
                ("Alice", "alice@example.com"),
                ("Bob", "bob@example.com"),
            ]
        ):
            db.upsert_entry_version(
                entry_id="entry-1",
                kb_name="test-kb",
                commit_hash=f"{'a' * 39}{i}",
                author_name=name,
                author_email=email,
                commit_date=f"2025-01-{20 + i:02d}T10:00:00",
                message=f"Commit {i}",
            )

        contributors = db.get_contributors("test-kb")
        assert len(contributors) == 2
        # Alice has more commits, should be first
        assert contributors[0]["author_name"] == "Alice"
        assert contributors[0]["commits"] == 2


class TestEntryAttribution:
    """Tests for created_by/modified_by on Entry."""

    def test_created_by_set_on_insert(self, db):
        """created_by is stored on entry insert."""
        db.register_kb("test-kb", KBType.RESEARCH, "/tmp/test")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Test",
                "body": "",
                "created_by": "alice",
                "modified_by": "alice",
            }
        )

        entry = db.get_entry("entry-1", "test-kb")
        assert entry["created_by"] == "alice"
        assert entry["modified_by"] == "alice"

    def test_created_by_preserved_on_update(self, db):
        """created_by is not overwritten on update."""
        db.register_kb("test-kb", KBType.RESEARCH, "/tmp/test")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Test",
                "body": "",
                "created_by": "alice",
                "modified_by": "alice",
            }
        )

        # Update with different modified_by
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Updated Test",
                "body": "Updated body",
                "created_by": "bob",  # Should NOT overwrite
                "modified_by": "bob",
            }
        )

        entry = db.get_entry("entry-1", "test-kb")
        assert entry["created_by"] == "alice"  # Preserved
        assert entry["modified_by"] == "bob"  # Updated

    def test_attribution_nullable(self, db):
        """Entries without attribution work fine (backward compat)."""
        db.register_kb("test-kb", KBType.RESEARCH, "/tmp/test")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Test",
                "body": "",
            }
        )

        entry = db.get_entry("entry-1", "test-kb")
        assert entry["created_by"] is None
        assert entry["modified_by"] is None


class TestKBRepoAssociation:
    """Tests for KB <-> Repo relationship."""

    def test_kb_with_repo_id(self, db):
        """KB can be linked to a repo."""
        repo = db.register_repo("org/kb", "/tmp/test")
        db.register_kb("test-kb", KBType.RESEARCH, "/tmp/test")

        # Link KB to repo
        db._raw_conn.execute(
            "UPDATE kb SET repo_id = ? WHERE name = ?",
            (repo["id"], "test-kb"),
        )
        db._raw_conn.commit()

        row = db._raw_conn.execute("SELECT repo_id FROM kb WHERE name = 'test-kb'").fetchone()
        assert row["repo_id"] == repo["id"]

    def test_kb_without_repo(self, db):
        """Standalone KBs have NULL repo_id."""
        db.register_kb("standalone", KBType.RESEARCH, "/tmp/standalone")
        row = db._raw_conn.execute("SELECT repo_id FROM kb WHERE name = 'standalone'").fetchone()
        assert row["repo_id"] is None


class TestSchemaVersion:
    """Tests for migration version."""

    def test_schema_version_is_6(self, db):
        """DB should be at schema version 6 after migration."""
        version = db.get_schema_version()
        assert version == 6

    def test_collaboration_tables_exist(self, db):
        """All collaboration tables should exist."""
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()

        assert "user" in table_names
        assert "repo" in table_names
        assert "workspace_repo" in table_names
        assert "entry_version" in table_names
