"""Unit tests for AuthService.oauth_login()."""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import AuthConfig, OAuthProviderConfig
from pyrite.services.auth_service import AuthService
from pyrite.services.oauth_providers import OAuthProfile
from pyrite.storage.database import PyriteDB


@pytest.fixture
def db_and_service():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = PyriteDB(db_path)
        config = AuthConfig(enabled=True, allow_registration=True)
        service = AuthService(db, config)
        yield db, service


@pytest.fixture
def github_profile():
    return OAuthProfile(
        provider="github",
        provider_id="12345",
        username="octocat",
        display_name="The Octocat",
        email="octocat@github.com",
        avatar_url="https://avatars.githubusercontent.com/u/12345",
        orgs=["my-org", "other-org"],
    )


@pytest.fixture
def provider_config():
    return OAuthProviderConfig(
        client_id="test-id",
        client_secret="test-secret",
        default_tier="read",
    )


class TestOAuthLoginNewUser:
    def test_new_user(self, db_and_service, github_profile, provider_config):
        _, service = db_and_service
        user, token = service.oauth_login(github_profile, provider_config)

        assert user["username"] == "octocat"
        assert user["auth_provider"] == "github"
        assert user["avatar_url"] == "https://avatars.githubusercontent.com/u/12345"
        assert user["role"] == "admin"  # first user gets admin
        assert token  # non-empty

    def test_second_oauth_user_gets_default_tier(self, db_and_service, provider_config):
        _, service = db_and_service
        # First user
        profile1 = OAuthProfile(
            provider="github",
            provider_id="111",
            username="first",
            orgs=[],
            display_name="First",
        )
        service.oauth_login(profile1, provider_config)

        # Second user
        profile2 = OAuthProfile(
            provider="github",
            provider_id="222",
            username="second",
            orgs=[],
            display_name="Second",
        )
        user2, _ = service.oauth_login(profile2, provider_config)
        assert user2["role"] == "read"


class TestOAuthLoginExistingUser:
    def test_existing_oauth_user(self, db_and_service, github_profile, provider_config):
        _, service = db_and_service
        user1, _ = service.oauth_login(github_profile, provider_config)

        # Login again — should update, not create
        github_profile.display_name = "Updated Name"
        user2, token2 = service.oauth_login(github_profile, provider_config)

        assert user2["id"] == user1["id"]
        assert user2["display_name"] == "Updated Name"
        assert token2


class TestUsernameConflict:
    def test_username_conflict(self, db_and_service, github_profile, provider_config):
        _, service = db_and_service
        # Create a local user with same username
        service.register("octocat", "password123")

        # OAuth login should prefix
        user, _ = service.oauth_login(github_profile, provider_config)
        assert user["username"] == "github:octocat"


class TestOrgRestriction:
    def test_org_restriction_blocks(self, db_and_service, provider_config):
        _, service = db_and_service
        provider_config.allowed_orgs = ["allowed-org"]
        profile = OAuthProfile(
            provider="github",
            provider_id="999",
            username="blocked",
            orgs=["other-org"],
            display_name="Blocked",
        )
        with pytest.raises(ValueError, match="not a member"):
            service.oauth_login(profile, provider_config)

    def test_org_restriction_allows(self, db_and_service, provider_config):
        _, service = db_and_service
        provider_config.allowed_orgs = ["allowed-org"]
        profile = OAuthProfile(
            provider="github",
            provider_id="888",
            username="allowed",
            orgs=["allowed-org", "other"],
            display_name="Allowed",
        )
        user, _ = service.oauth_login(profile, provider_config)
        assert user["username"] == "allowed"


class TestTierFromOrgMap:
    def test_tier_from_org_map(self, db_and_service, github_profile, provider_config):
        _, service = db_and_service
        provider_config.org_tier_map = {"my-org": "write", "other-org": "read"}
        # First create a local user so this one isn't admin
        service.register("localuser", "password123")

        user, _ = service.oauth_login(github_profile, provider_config)
        assert user["role"] == "write"  # highest match

    def test_tier_highest_wins(self, db_and_service, provider_config):
        _, service = db_and_service
        provider_config.org_tier_map = {"org-a": "read", "org-b": "admin"}
        # Seed a local user first so OAuth user isn't auto-admin
        service.register("seeduser", "password123")

        profile = OAuthProfile(
            provider="github",
            provider_id="777",
            username="multi",
            orgs=["org-a", "org-b"],
            display_name="Multi",
        )
        user, _ = service.oauth_login(profile, provider_config)
        assert user["role"] == "admin"


class TestLocalLoginBlockedForOAuthUser:
    def test_local_login_blocked_for_oauth_user(
        self, db_and_service, github_profile, provider_config
    ):
        _, service = db_and_service
        service.oauth_login(github_profile, provider_config)

        with pytest.raises(ValueError, match="external authentication"):
            service.login("octocat", "anything")
