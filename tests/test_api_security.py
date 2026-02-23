"""
Tests for REST API security: CORS configuration and API key authentication.
"""

import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db
from pyrite.storage.database import PyriteDB


def _make_client(cors_origins=None, api_key="", tmpdir=None):
    """Create a TestClient with a fresh app using the given security settings."""
    if cors_origins is None:
        cors_origins = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8088"]

    db_path = tmpdir / "index.db"
    kb_path = tmpdir / "kb"
    kb_path.mkdir(exist_ok=True)

    config = PyriteConfig(
        knowledge_bases=[
            KBConfig(name="test-kb", path=kb_path, kb_type="generic"),
        ],
        settings=Settings(
            index_path=db_path,
            cors_origins=cors_origins,
            api_key=api_key,
        ),
    )

    application = create_app(config=config)

    # Override dependencies to use test config and DB
    db = PyriteDB(db_path)
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_db] = lambda: db

    return TestClient(application)


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def client_no_auth(tmpdir):
    """App with no API key (auth disabled)."""
    return _make_client(api_key="", tmpdir=tmpdir)


@pytest.fixture
def client_with_auth(tmpdir):
    """App with API key auth enabled."""
    return _make_client(api_key="test-secret-key", tmpdir=tmpdir)


@pytest.fixture
def client_custom_cors(tmpdir):
    """App with custom CORS origins."""
    return _make_client(cors_origins=["https://myapp.example.com"], tmpdir=tmpdir)


@pytest.fixture
def client_wildcard_cors(tmpdir):
    """App with wildcard CORS origins."""
    return _make_client(cors_origins=["*"], tmpdir=tmpdir)


# =============================================================================
# CORS Tests
# =============================================================================


class TestCORS:
    """Test CORS middleware configuration."""

    def test_configured_origin_allowed(self, client_custom_cors):
        resp = client_custom_cors.get(
            "/health",
            headers={"Origin": "https://myapp.example.com"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "https://myapp.example.com"

    def test_unconfigured_origin_rejected(self, client_custom_cors):
        resp = client_custom_cors.get(
            "/health",
            headers={"Origin": "https://evil.example.com"},
        )
        assert resp.status_code == 200  # Request succeeds but no CORS header
        assert "access-control-allow-origin" not in resp.headers

    def test_default_origins_allow_localhost(self, client_no_auth):
        resp = client_no_auth.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_wildcard_cors_no_credentials(self, client_wildcard_cors):
        """When origins is ['*'], allow_credentials should be False (spec compliance)."""
        resp = client_wildcard_cors.get(
            "/health",
            headers={"Origin": "https://anything.example.com"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "*"
        # Credentials should NOT be allowed with wildcard (spec compliance)
        assert resp.headers.get("access-control-allow-credentials") != "true"

    def test_preflight_request(self, client_custom_cors):
        resp = client_custom_cors.options(
            "/health",
            headers={
                "Origin": "https://myapp.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "https://myapp.example.com"


# =============================================================================
# API Key Auth Tests
# =============================================================================


class TestAPIKeyAuth:
    """Test API key authentication."""

    def test_health_always_accessible_without_auth(self, client_with_auth):
        """Health endpoint should never require auth."""
        resp = client_with_auth.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_protected_endpoint_rejected_without_key(self, client_with_auth):
        """Endpoints should return 401 when API key is configured but not provided."""
        resp = client_with_auth.get("/api/kbs")
        assert resp.status_code == 401
        assert "Invalid or missing API key" in resp.json()["detail"]

    def test_protected_endpoint_rejected_with_wrong_key(self, client_with_auth):
        """Endpoints should return 401 with an incorrect API key."""
        resp = client_with_auth.get("/api/kbs", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_protected_endpoint_succeeds_with_correct_header(self, client_with_auth):
        """Endpoints should succeed with correct X-API-Key header."""
        resp = client_with_auth.get("/api/kbs", headers={"X-API-Key": "test-secret-key"})
        assert resp.status_code == 200

    def test_protected_endpoint_succeeds_with_query_param(self, client_with_auth):
        """Endpoints should succeed with correct api_key query param."""
        resp = client_with_auth.get("/kbs?api_key=test-secret-key")
        assert resp.status_code == 200

    def test_auth_disabled_when_key_empty(self, client_no_auth):
        """All endpoints accessible when api_key is empty (backwards-compatible)."""
        resp = client_no_auth.get("/api/kbs")
        assert resp.status_code == 200

    def test_multiple_endpoints_require_auth(self, client_with_auth):
        """Verify several endpoints all require auth."""
        endpoints = [
            ("GET", "/api/kbs"),
            ("GET", "/api/tags"),
            ("GET", "/api/stats"),
            ("GET", "/api/timeline"),
        ]
        for method, path in endpoints:
            resp = client_with_auth.request(method, path)
            assert resp.status_code == 401, f"{method} {path} should require auth"

    def test_multiple_endpoints_pass_with_key(self, client_with_auth):
        """Verify several endpoints all accept valid auth."""
        headers = {"X-API-Key": "test-secret-key"}
        endpoints = [
            ("GET", "/api/kbs"),
            ("GET", "/api/tags"),
            ("GET", "/api/timeline"),
        ]
        for method, path in endpoints:
            resp = client_with_auth.request(method, path, headers=headers)
            assert resp.status_code == 200, f"{method} {path} should succeed with valid key"


# =============================================================================
# Config Serialization Tests
# =============================================================================


class TestSecurityConfig:
    """Test that security settings serialize/deserialize correctly."""

    def test_settings_defaults(self):
        settings = Settings()
        assert settings.cors_origins == [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8088",
        ]
        assert settings.api_key == ""

    def test_config_round_trip(self):
        config = PyriteConfig(
            settings=Settings(
                cors_origins=["https://app.example.com"],
                api_key="my-secret",
            )
        )
        data = config.to_dict()
        assert data["settings"]["cors_origins"] == ["https://app.example.com"]
        assert data["settings"]["api_key"] == "my-secret"

        restored = PyriteConfig.from_dict(data)
        assert restored.settings.cors_origins == ["https://app.example.com"]
        assert restored.settings.api_key == "my-secret"

    def test_from_dict_defaults(self):
        """from_dict with empty settings should use defaults."""
        config = PyriteConfig.from_dict({"settings": {}})
        assert config.settings.cors_origins == [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8088",
        ]
        assert config.settings.api_key == ""
