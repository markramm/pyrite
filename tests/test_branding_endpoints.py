"""Tests for the public /config/branding and /branding/{file} endpoints.

These endpoints live OUTSIDE /api (no auth required) so the login page
can fetch branding before the user is authenticated.
"""

import textwrap
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app


def _make_client(branding_dir: Path | None = None, tmpdir: Path | None = None) -> TestClient:
    """Create a TestClient with a configurable branding dir."""
    assert tmpdir is not None
    db_path = tmpdir / "index.db"
    kb_path = tmpdir / "kb"
    kb_path.mkdir(exist_ok=True)

    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="generic")],
        settings=Settings(index_path=db_path, branding_dir=branding_dir),
    )
    app = create_app(config=config)
    return TestClient(app)


@pytest.fixture
def populated_branding_dir(tmp_path: Path) -> Path:
    d = tmp_path / "branding"
    d.mkdir()
    (d / "branding.yaml").write_text(
        textwrap.dedent(
            """
            name: "Transparency Cascade Press"
            primary_color: "#c93b3b"
            logo: "logo.png"
            wordmark: "wordmark.png"
            invert_on_dark: true
            footer_credit_url: "https://pyrite.wiki"
            meta:
              description: "Investigative journalism."
            """
        ).lstrip()
    )
    (d / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\nfake-logo")
    (d / "wordmark.png").write_bytes(b"\x89PNG\r\n\x1a\nfake-wordmark")
    return d


# ---------------------------------------------------------------------------
# GET /config/branding
# ---------------------------------------------------------------------------


class TestBrandingConfigEndpoint:
    def test_returns_200_without_auth(self, populated_branding_dir, tmp_path):
        client = _make_client(branding_dir=populated_branding_dir, tmpdir=tmp_path)
        r = client.get("/config/branding")
        assert r.status_code == 200

    def test_returns_branded_values(self, populated_branding_dir, tmp_path):
        client = _make_client(branding_dir=populated_branding_dir, tmpdir=tmp_path)
        data = client.get("/config/branding").json()
        assert data["name"] == "Transparency Cascade Press"
        assert data["primary_color"] == "#c93b3b"
        assert data["logo_url"] == "/branding/logo.png"
        assert data["wordmark_url"] == "/branding/wordmark.png"
        assert data["invert_on_dark"] is True

    def test_returns_defaults_when_no_branding_dir(self, tmp_path):
        client = _make_client(branding_dir=None, tmpdir=tmp_path)
        data = client.get("/config/branding").json()
        assert data["name"] == "Pyrite"
        assert data["logo_url"] is None

    def test_response_is_cacheable(self, populated_branding_dir, tmp_path):
        client = _make_client(branding_dir=populated_branding_dir, tmpdir=tmp_path)
        r = client.get("/config/branding")
        # Any Cache-Control header is fine; just verify caching hasn't been
        # explicitly disabled.
        assert "no-store" not in r.headers.get("cache-control", "").lower()


# ---------------------------------------------------------------------------
# GET /branding/{filename}
# ---------------------------------------------------------------------------


class TestBrandingAssetEndpoint:
    def test_serves_logo_without_auth(self, populated_branding_dir, tmp_path):
        client = _make_client(branding_dir=populated_branding_dir, tmpdir=tmp_path)
        r = client.get("/branding/logo.png")
        assert r.status_code == 200
        assert r.content == b"\x89PNG\r\n\x1a\nfake-logo"
        # PNG content-type
        assert "image/png" in r.headers["content-type"]

    def test_serves_wordmark(self, populated_branding_dir, tmp_path):
        client = _make_client(branding_dir=populated_branding_dir, tmpdir=tmp_path)
        r = client.get("/branding/wordmark.png")
        assert r.status_code == 200
        assert r.content.endswith(b"fake-wordmark")

    def test_404_for_missing_file(self, populated_branding_dir, tmp_path):
        client = _make_client(branding_dir=populated_branding_dir, tmpdir=tmp_path)
        r = client.get("/branding/does-not-exist.png")
        assert r.status_code == 404

    def test_404_when_no_branding_dir_configured(self, tmp_path):
        client = _make_client(branding_dir=None, tmpdir=tmp_path)
        r = client.get("/branding/anything.png")
        assert r.status_code == 404

    def test_traversal_cannot_leak_adjacent_files(self, populated_branding_dir, tmp_path):
        """An adjacent file next to the branding dir must not be reachable.

        HTTP clients typically normalize ``..`` before the request reaches
        the server (so the endpoint handler never sees it). That's the
        first line of defense; the resolver itself is tested in
        test_branding_service.py::test_resolve_asset_rejects_traversal.
        This test verifies the *outcome*: no adjacent file leaks out
        regardless of what normalization occurs.
        """
        # Write a sentinel file next to the branding dir.
        sentinel = populated_branding_dir.parent / "secret.txt"
        sentinel.write_text("SHOULD-NOT-LEAK")

        client = _make_client(branding_dir=populated_branding_dir, tmpdir=tmp_path)
        for url in (
            "/branding/%2E%2E/secret.txt",
            "/branding/../secret.txt",
            "/branding//secret.txt",
        ):
            r = client.get(url)
            assert "SHOULD-NOT-LEAK" not in r.text, f"leaked via {url}"
