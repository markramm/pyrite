"""Tests for GET /sitemap.xml and GET /robots.txt (pyrite-dynamic-sitemap).

The sitemap enumerates entries in public KBs so crawlers can index
the live app. Once the `kb.yaml: published: true` flag ships, the
query switches to that; until then we use `default_role == "read"` as
the "public" signal.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app
from pyrite.storage.database import PyriteDB


SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def _make_env(
    tmp_path: Path,
    kbs: list[tuple[str, str | None]],  # [(name, default_role)]
    entries: list[dict] | None = None,
    *,
    branding_dir: Path | None = None,
) -> TestClient:
    """Build a TestClient with the given KBs + entries seeded."""
    db_path = tmp_path / "index.db"
    kb_configs = []
    for name, role in kbs:
        kb_path = tmp_path / name
        kb_path.mkdir()
        kb_configs.append(KBConfig(name=name, path=kb_path, kb_type="generic", default_role=role))

    config = PyriteConfig(
        knowledge_bases=kb_configs,
        settings=Settings(index_path=db_path, branding_dir=branding_dir),
    )

    db = PyriteDB(db_path)
    for kb_conf in kb_configs:
        db.register_kb(kb_conf.name, "generic", str(kb_conf.path), "")
    for entry in entries or []:
        full = {
            "entry_type": "note",
            "body": "",
            "summary": "",
            "tags": [],
            "sources": [],
            "links": [],
            "metadata": {},
            **entry,
        }
        db.upsert_entry(full)
    db.close()

    return TestClient(create_app(config=config))


# ---------------------------------------------------------------------------
# /sitemap.xml
# ---------------------------------------------------------------------------


class TestSitemapXml:
    def test_returns_valid_xml_with_correct_namespace(self, tmp_path):
        client = _make_env(
            tmp_path,
            [("public-kb", "read")],
            [
                {"id": "a", "kb_name": "public-kb", "title": "Entry A"},
                {"id": "b", "kb_name": "public-kb", "title": "Entry B"},
            ],
        )
        r = client.get("/sitemap.xml")
        assert r.status_code == 200
        assert "xml" in r.headers["content-type"]

        root = ET.fromstring(r.text)
        assert root.tag == f"{SITEMAP_NS}urlset"

    def test_enumerates_public_kb_entries(self, tmp_path):
        client = _make_env(
            tmp_path,
            [("public-kb", "read")],
            [
                {"id": "a", "kb_name": "public-kb", "title": "Entry A"},
                {"id": "b", "kb_name": "public-kb", "title": "Entry B"},
            ],
        )
        r = client.get("/sitemap.xml")
        root = ET.fromstring(r.text)
        locs = {u.findtext(f"{SITEMAP_NS}loc") for u in root.findall(f"{SITEMAP_NS}url")}
        # Paths include the live-app entry URL for each entry
        assert any("/entries/a" in loc for loc in locs if loc)
        assert any("/entries/b" in loc for loc in locs if loc)

    def test_excludes_private_kbs(self, tmp_path):
        client = _make_env(
            tmp_path,
            [("public-kb", "read"), ("private-kb", "none")],
            [
                {"id": "pub", "kb_name": "public-kb", "title": "Public"},
                {"id": "priv", "kb_name": "private-kb", "title": "Private"},
            ],
        )
        r = client.get("/sitemap.xml")
        root = ET.fromstring(r.text)
        locs = " ".join(
            u.findtext(f"{SITEMAP_NS}loc") or "" for u in root.findall(f"{SITEMAP_NS}url")
        )
        assert "/entries/pub" in locs
        assert "priv" not in locs

    def test_excludes_kbs_with_no_default_role_set(self, tmp_path):
        """KBs with default_role=None fall back to the global default.
        Without explicit 'read' they are treated as non-public for sitemap.
        """
        client = _make_env(
            tmp_path,
            [("unknown-kb", None)],
            [{"id": "x", "kb_name": "unknown-kb", "title": "X"}],
        )
        r = client.get("/sitemap.xml")
        root = ET.fromstring(r.text)
        locs = [u.findtext(f"{SITEMAP_NS}loc") for u in root.findall(f"{SITEMAP_NS}url")]
        assert locs == []

    def test_uses_branding_site_url_when_set(self, tmp_path):
        branding_dir = tmp_path / "branding"
        branding_dir.mkdir()
        (branding_dir / "branding.yaml").write_text(
            textwrap.dedent(
                """
                name: "TCP"
                site_url: "https://investigate.example.org"
                """
            ).lstrip()
        )
        client = _make_env(
            tmp_path,
            [("public-kb", "read")],
            [{"id": "a", "kb_name": "public-kb", "title": "A"}],
            branding_dir=branding_dir,
        )
        r = client.get("/sitemap.xml")
        assert "https://investigate.example.org/entries/a" in r.text

    def test_lastmod_reflects_updated_at(self, tmp_path):
        client = _make_env(
            tmp_path,
            [("public-kb", "read")],
            [
                {
                    "id": "a",
                    "kb_name": "public-kb",
                    "title": "A",
                    "updated_at": "2026-04-23T12:00:00",
                }
            ],
        )
        r = client.get("/sitemap.xml")
        root = ET.fromstring(r.text)
        url = root.find(f"{SITEMAP_NS}url")
        assert url is not None
        lastmod = url.findtext(f"{SITEMAP_NS}lastmod")
        assert lastmod == "2026-04-23T12:00:00"

    def test_empty_when_no_public_kbs(self, tmp_path):
        client = _make_env(
            tmp_path,
            [("priv", "none")],
            [{"id": "a", "kb_name": "priv", "title": "A"}],
        )
        r = client.get("/sitemap.xml")
        root = ET.fromstring(r.text)
        assert root.findall(f"{SITEMAP_NS}url") == []

    def test_public_no_auth_required(self, tmp_path):
        """Sitemap must be reachable without any auth — crawlers don't sign in."""
        client = _make_env(
            tmp_path, [("public-kb", "read")], [{"id": "a", "kb_name": "public-kb", "title": "A"}]
        )
        # No Authorization header, no session cookie.
        r = client.get("/sitemap.xml")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# /robots.txt
# ---------------------------------------------------------------------------


class TestRobotsTxt:
    def test_returns_200_plain_text(self, tmp_path):
        client = _make_env(tmp_path, [("public-kb", "read")], [])
        r = client.get("/robots.txt")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]

    def test_points_at_sitemap(self, tmp_path):
        client = _make_env(tmp_path, [("public-kb", "read")], [])
        r = client.get("/robots.txt")
        assert "Sitemap:" in r.text
        assert "/sitemap.xml" in r.text

    def test_allow_all_by_default(self, tmp_path):
        client = _make_env(tmp_path, [("public-kb", "read")], [])
        r = client.get("/robots.txt")
        assert "User-agent: *" in r.text
        assert "Allow: /" in r.text

    def test_uses_branding_site_url(self, tmp_path):
        branding_dir = tmp_path / "branding"
        branding_dir.mkdir()
        (branding_dir / "branding.yaml").write_text('site_url: "https://example.org"\n')
        client = _make_env(tmp_path, [("public-kb", "read")], [], branding_dir=branding_dir)
        r = client.get("/robots.txt")
        assert "https://example.org/sitemap.xml" in r.text
