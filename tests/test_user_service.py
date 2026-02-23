"""Tests for UserService."""

import tempfile
from pathlib import Path

import pytest

from pyrite.services.user_service import UserService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def db():
    """Create a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = PyriteDB(db_path)
        yield db
        db.close()


@pytest.fixture
def user_service(db):
    """Create a UserService instance."""
    return UserService(db)


class TestUserService:
    """Tests for UserService."""

    def test_get_local_user(self, user_service):
        """get_local_user returns the sentinel user."""
        user = user_service.get_local_user()
        assert user["github_login"] == "local"
        assert user["github_id"] == 0

    def test_get_or_create_from_github(self, user_service):
        """get_or_create_from_github creates a new user."""
        user = user_service.get_or_create_from_github(
            "alice", 100, "Alice", "https://avatar.url", "alice@example.com"
        )
        assert user["github_login"] == "alice"
        assert user["display_name"] == "Alice"

    def test_get_or_create_from_github_updates(self, user_service):
        """get_or_create_from_github updates existing user."""
        user_service.get_or_create_from_github("alice", 100, "Alice")
        updated = user_service.get_or_create_from_github("alice-new", 100, "Alice Updated")
        assert updated["github_login"] == "alice-new"
        assert updated["display_name"] == "Alice Updated"

    def test_get_current_user_without_auth(self, user_service):
        """get_current_user returns local user when no GitHub auth."""
        user = user_service.get_current_user()
        assert user["github_login"] == "local"

    def test_resolve_git_author_by_email(self, user_service, db):
        """resolve_git_author matches by email."""
        db.upsert_user("alice", 100, "Alice", "", "alice@example.com")
        login = user_service.resolve_git_author("Alice Smith", "alice@example.com")
        assert login == "alice"

    def test_resolve_git_author_noreply(self, user_service, db):
        """resolve_git_author handles GitHub noreply emails."""
        db.upsert_user("alice", 100, "Alice")
        login = user_service.resolve_git_author("Alice", "100+alice@users.noreply.github.com")
        assert login == "alice"

    def test_resolve_git_author_no_match(self, user_service):
        """resolve_git_author returns None when no match."""
        login = user_service.resolve_git_author("Unknown", "unknown@example.com")
        assert login is None

    def test_get_or_create_default_display_name(self, user_service):
        """Display name defaults to login when empty."""
        user = user_service.get_or_create_from_github("bob", 200)
        assert user["display_name"] == "bob"
