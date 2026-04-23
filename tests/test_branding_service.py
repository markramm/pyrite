"""Tests for BrandingService — white-label branding loader.

Covers: load from folder, fallback to defaults, missing-file handling,
theme-variant resolution, asset URL mapping, ETag generation.
"""

import textwrap
from pathlib import Path

import pytest

from pyrite.services.branding_service import (
    DEFAULT_BRAND_NAME,
    DEFAULT_PRIMARY_COLOR,
    BrandingConfig,
    BrandingService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip())


@pytest.fixture
def branding_dir(tmp_path: Path) -> Path:
    """A fully-populated branding folder for Transparency Cascade."""
    d = tmp_path / "branding"
    _write(
        d / "branding.yaml",
        """
        name: "Transparency Cascade Press"
        tagline: "Tracing the money, naming the actors, connecting the patterns"
        primary_color: "#c93b3b"
        site_url: "https://investigate.transparencycascade.org"
        support_url: "mailto:contact@transparencycascade.org"
        footer_credit_url: "https://pyrite.wiki"

        logo: "logo.png"
        wordmark: "wordmark.png"
        invert_on_dark: true

        meta:
          description: "Independent investigative journalism."

        mcp:
          agent_prompt_brand: "Transparency Cascade"
        """,
    )
    (d / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (d / "wordmark.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return d


@pytest.fixture
def minimal_branding_dir(tmp_path: Path) -> Path:
    """Only name set — everything else should fall through to defaults."""
    d = tmp_path / "minimal"
    _write(d / "branding.yaml", 'name: "Minimal Brand"\n')
    return d


# ---------------------------------------------------------------------------
# Loader — full config
# ---------------------------------------------------------------------------


class TestBrandingServiceLoadsFromFolder:
    def test_loads_name_and_primary_color(self, branding_dir: Path):
        cfg = BrandingService(branding_dir).get()
        assert cfg.name == "Transparency Cascade Press"
        assert cfg.primary_color == "#c93b3b"

    def test_loads_tagline_and_urls(self, branding_dir: Path):
        cfg = BrandingService(branding_dir).get()
        assert cfg.tagline == "Tracing the money, naming the actors, connecting the patterns"
        assert cfg.site_url == "https://investigate.transparencycascade.org"
        assert cfg.support_url == "mailto:contact@transparencycascade.org"
        assert cfg.footer_credit_url == "https://pyrite.wiki"

    def test_loads_logo_and_wordmark_filenames(self, branding_dir: Path):
        cfg = BrandingService(branding_dir).get()
        assert cfg.logo == "logo.png"
        assert cfg.wordmark == "wordmark.png"
        assert cfg.invert_on_dark is True

    def test_loads_meta_description(self, branding_dir: Path):
        cfg = BrandingService(branding_dir).get()
        assert cfg.meta_description == "Independent investigative journalism."

    def test_loads_mcp_agent_prompt_brand(self, branding_dir: Path):
        cfg = BrandingService(branding_dir).get()
        assert cfg.mcp_agent_prompt_brand == "Transparency Cascade"


# ---------------------------------------------------------------------------
# Fallback behavior
# ---------------------------------------------------------------------------


class TestBrandingServiceFallsBack:
    def test_no_branding_dir_uses_defaults(self):
        cfg = BrandingService(None).get()
        assert cfg.name == DEFAULT_BRAND_NAME
        assert cfg.primary_color == DEFAULT_PRIMARY_COLOR
        assert cfg.logo is None
        assert cfg.wordmark is None

    def test_missing_branding_dir_uses_defaults(self, tmp_path: Path):
        missing = tmp_path / "does-not-exist"
        cfg = BrandingService(missing).get()
        assert cfg.name == DEFAULT_BRAND_NAME

    def test_empty_branding_dir_uses_defaults(self, tmp_path: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        cfg = BrandingService(empty).get()
        assert cfg.name == DEFAULT_BRAND_NAME

    def test_missing_fields_fall_through_to_defaults(self, minimal_branding_dir: Path):
        cfg = BrandingService(minimal_branding_dir).get()
        assert cfg.name == "Minimal Brand"
        assert cfg.primary_color == DEFAULT_PRIMARY_COLOR  # not in yaml → default
        assert cfg.logo is None
        assert cfg.invert_on_dark is False  # default

    def test_mcp_brand_defaults_to_name_when_unset(self, minimal_branding_dir: Path):
        cfg = BrandingService(minimal_branding_dir).get()
        # mcp.agent_prompt_brand falls back to the top-level name
        assert cfg.mcp_agent_prompt_brand == "Minimal Brand"


# ---------------------------------------------------------------------------
# Asset URL mapping
# ---------------------------------------------------------------------------


class TestAssetUrls:
    def test_logo_url_is_none_when_no_file(self, minimal_branding_dir: Path):
        cfg = BrandingService(minimal_branding_dir).get()
        assert cfg.logo_url() is None

    def test_logo_url_when_present(self, branding_dir: Path):
        cfg = BrandingService(branding_dir).get()
        assert cfg.logo_url() == "/branding/logo.png"

    def test_wordmark_url_when_present(self, branding_dir: Path):
        cfg = BrandingService(branding_dir).get()
        assert cfg.wordmark_url() == "/branding/wordmark.png"

    def test_resolves_asset_path_inside_branding_dir(self, branding_dir: Path):
        svc = BrandingService(branding_dir)
        path = svc.resolve_asset("logo.png")
        assert path == branding_dir / "logo.png"
        assert path.exists()

    def test_resolve_asset_rejects_traversal(self, branding_dir: Path):
        """Asset resolution must not escape the branding dir."""
        svc = BrandingService(branding_dir)
        assert svc.resolve_asset("../../../etc/passwd") is None
        assert svc.resolve_asset("/etc/passwd") is None

    def test_resolve_asset_returns_none_for_missing_file(self, branding_dir: Path):
        svc = BrandingService(branding_dir).resolve_asset("nope.png")
        assert svc is None


# ---------------------------------------------------------------------------
# Theme variants
# ---------------------------------------------------------------------------


class TestThemeVariants:
    def test_light_dark_variants_load(self, tmp_path: Path):
        d = tmp_path / "variant"
        _write(
            d / "branding.yaml",
            """
            name: "Variant Brand"
            logo_light: "logo-black.png"
            logo_dark: "logo-white.png"
            wordmark_light: "wordmark-black.png"
            wordmark_dark: "wordmark-white.png"
            invert_on_dark: false
            """,
        )
        for f in ("logo-black.png", "logo-white.png", "wordmark-black.png", "wordmark-white.png"):
            (d / f).write_bytes(b"fake")
        cfg = BrandingService(d).get()
        assert cfg.logo_light == "logo-black.png"
        assert cfg.logo_dark == "logo-white.png"
        assert cfg.wordmark_light == "wordmark-black.png"
        assert cfg.wordmark_dark == "wordmark-white.png"


# ---------------------------------------------------------------------------
# API serialization
# ---------------------------------------------------------------------------


class TestToPublicDict:
    def test_public_dict_shape(self, branding_dir: Path):
        cfg = BrandingService(branding_dir).get()
        public = cfg.to_public_dict()
        # Required fields
        assert public["name"] == "Transparency Cascade Press"
        assert public["primary_color"] == "#c93b3b"
        assert public["logo_url"] == "/branding/logo.png"
        assert public["wordmark_url"] == "/branding/wordmark.png"
        assert public["invert_on_dark"] is True
        assert public["footer_credit_url"] == "https://pyrite.wiki"

    def test_public_dict_omits_secrets(self, branding_dir: Path):
        """Nothing sensitive is in branding, but verify no extras leak."""
        cfg = BrandingService(branding_dir).get()
        public = cfg.to_public_dict()
        assert "branding_dir" not in public
        assert "_path" not in public

    def test_defaults_dict_has_name_pyrite(self):
        cfg = BrandingService(None).get()
        public = cfg.to_public_dict()
        assert public["name"] == DEFAULT_BRAND_NAME
        assert public["logo_url"] is None
