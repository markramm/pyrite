"""Unit tests for GitHubOAuthProvider with mocked httpx."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pyrite.services.oauth_providers import GitHubOAuthProvider, OAuthToken


@pytest.fixture
def provider():
    return GitHubOAuthProvider(client_id="test-id", client_secret="test-secret")


def _mock_httpx_client(**kwargs):
    """Create a mock httpx.AsyncClient with async context manager support."""
    mock_client = AsyncMock()
    for k, v in kwargs.items():
        setattr(mock_client, k, v)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestGetAuthorizeUrl:
    def test_contains_client_id(self, provider):
        url = provider.get_authorize_url("http://localhost/callback", "state123")
        assert "client_id=test-id" in url
        assert "state=state123" in url
        assert "redirect_uri=http" in url
        assert "scope=read%3Auser+read%3Aorg" in url

    def test_starts_with_github(self, provider):
        url = provider.get_authorize_url("http://localhost/callback", "s")
        assert url.startswith("https://github.com/login/oauth/authorize")


class TestExchangeCode:
    def test_exchange_code_success(self, provider):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "gho_abc123",
            "token_type": "bearer",
            "scope": "read:user,read:org",
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = _mock_httpx_client(post=AsyncMock(return_value=mock_resp))

        with patch("pyrite.services.oauth_providers.httpx.AsyncClient", return_value=mock_client):
            token = asyncio.run(provider.exchange_code("code123", "http://localhost/callback"))

        assert token.access_token == "gho_abc123"
        assert token.token_type == "bearer"

    def test_exchange_code_error(self, provider):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect or expired.",
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = _mock_httpx_client(post=AsyncMock(return_value=mock_resp))

        with patch("pyrite.services.oauth_providers.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="token exchange failed"):
                asyncio.run(provider.exchange_code("bad", "http://localhost/callback"))


class TestGetUserProfile:
    def test_get_user_profile(self, provider):
        token = OAuthToken(access_token="gho_abc123")

        user_resp = MagicMock()
        user_resp.json.return_value = {
            "id": 12345,
            "login": "octocat",
            "name": "The Octocat",
            "email": "octocat@github.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        }
        user_resp.raise_for_status = MagicMock()

        orgs_resp = MagicMock()
        orgs_resp.json.return_value = [
            {"login": "github"},
            {"login": "octo-org"},
        ]
        orgs_resp.raise_for_status = MagicMock()

        mock_client = _mock_httpx_client(get=AsyncMock(side_effect=[user_resp, orgs_resp]))

        with patch("pyrite.services.oauth_providers.httpx.AsyncClient", return_value=mock_client):
            profile = asyncio.run(provider.get_user_profile(token))

        assert profile.provider == "github"
        assert profile.provider_id == "12345"
        assert profile.username == "octocat"
        assert profile.display_name == "The Octocat"
        assert profile.email == "octocat@github.com"
        assert profile.orgs == ["github", "octo-org"]
