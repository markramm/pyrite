"""Stored XSS in the pre-rendered /site pages.

`_md_to_html` and `_md_inline` passed raw HTML in entry bodies straight
through (only link text and hrefs were escaped), and the JSON-LD block was
`json.dumps` inside `<script>`, which does not escape `</`. Anyone who can
write an entry could run script on the application's own origin, where it
can call `/api` with a visiting admin's session.

The property: KB content is HTML-escaped wherever the server emits it as
HTML, and never closes a `<script>` element it is embedded in. `/site`
responses also carry a Content-Security-Policy as defence in depth.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.site_cache import SiteCacheService, _md_inline, _md_to_html
from pyrite.storage.database import PyriteDB

KB = "pub-kb"

BODY_PAYLOADS = [
    "<script>alert('body-script')</script>",
    "<img src=x onerror=alert('body-img')>",
    "<svg onload=alert('body-svg')>",
    "### <img src=x onerror=alert('heading')>",
    "- <iframe src=javascript:alert('list')></iframe>",
    "**<b onmouseover=alert('bold')>x</b>**",
]
TITLE_BREAKOUT = "</script><script>alert('title')</script>"
AUTHOR_BREAKOUT = "</SCRIPT><script>alert('author')</script>"


class _Scan(HTMLParser):
    """Collect what a browser would treat as markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict]] = []
        self.scripts: list[tuple[dict, str]] = []
        self._in_script: dict | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if tag == "script":
            self._in_script, self._buf = a, []

    def handle_data(self, data):
        if self._in_script is not None:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_script is not None:
            self.scripts.append((self._in_script, "".join(self._buf)))
            self._in_script = None


def _assert_no_executable_payload(html: str) -> None:
    scan = _Scan()
    scan.feed(html)
    for tag, attrs in scan.tags:
        assert tag not in ("img", "svg", "iframe", "b"), f"payload tag emitted: <{tag} {attrs}>"
        handlers = [k for k in attrs if k.startswith("on")]
        assert not handlers, f"event handler emitted on <{tag}>: {handlers}"
    for attrs, text in scan.scripts:
        if attrs.get("type") == "application/ld+json":
            # A data block: inert as long as the whole element is one JSON
            # value (a breakout leaves a truncated, unparseable fragment).
            json.loads(text)
            continue
        assert "alert(" not in text, f"payload inside <script {attrs}>: {text[:120]}"


@pytest.fixture
def env(tmp_path):
    kb = KBConfig(name=KB, path=tmp_path / "kb", kb_type="generic", default_role="read")
    config = PyriteConfig(knowledge_bases=[kb], settings=Settings(index_path=tmp_path / "idx.db"))
    db = PyriteDB(tmp_path / "idx.db")
    db.register_kb(KB, "generic", str(tmp_path / "kb"), "")
    svc = SiteCacheService(config, db)
    yield {"db": db, "svc": svc, "cache": svc.cache_dir, "config": config, "tmp": tmp_path}
    db.close()


def _put(db, eid, title="T", body="", **extra):
    db.upsert_entry(
        {
            "id": eid,
            "kb_name": KB,
            "entry_type": "note",
            "title": title,
            "body": body,
            "summary": "",
            "tags": [],
            "sources": [],
            "links": [],
            "metadata": {},
            **extra,
        }
    )


class TestEntryBodyEscaped:
    @pytest.mark.parametrize("payload", BODY_PAYLOADS)
    def test_body_payload_is_inert(self, env, payload):
        _put(env["db"], "evil", body=f"Intro.\n\n{payload}\n\nOutro.")
        env["svc"].render_all()
        html = (env["cache"] / KB / "evil.html").read_text()
        _assert_no_executable_payload(html)

    def test_escaped_text_still_visible(self, env):
        _put(env["db"], "evil", body="Say <script>x</script> & more")
        env["svc"].render_all()
        html = (env["cache"] / KB / "evil.html").read_text()
        assert "&lt;script&gt;x&lt;/script&gt; &amp; more" in html


class TestJsonLdEscaped:
    def test_title_cannot_close_script(self, env):
        _put(env["db"], "evil", title=TITLE_BREAKOUT, body="b", created_by=AUTHOR_BREAKOUT)
        env["svc"].render_all()
        html = (env["cache"] / KB / "evil.html").read_text()
        _assert_no_executable_payload(html)

    def test_jsonld_round_trips_and_has_no_raw_angle_brackets(self, env):
        _put(env["db"], "evil", title="A <b> & </script> title", body="b")
        env["svc"].render_all()
        html = (env["cache"] / KB / "evil.html").read_text()
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        assert m, "JSON-LD block missing"
        raw = m.group(1)
        assert "<" not in raw and ">" not in raw and "&" not in raw
        assert json.loads(raw)["name"] == "A <b> & </script> title"


class TestHomepageEscaped:
    def test_homepage_sections_are_inert(self, env):
        body = (
            "Intro <img src=x onerror=alert('intro')> text.\n\n"
            "## The Cascade Pattern\n\n"
            "Pattern intro <svg onload=alert('cascade')>\n\n"
            "1. **Step** — does a thing\n\n"
            "## Data Standards\n\n"
            "<script>alert('standards')</script>\n\n"
            "## Explore\n\n"
            "[Click](javascript:alert('explore')) — a card\n"
        )
        _put(env["db"], "_homepage", title="Home", body=body)
        env["svc"].render_all()
        html = (env["cache"] / KB / "index.html").read_text()
        _assert_no_executable_payload(html)
        assert "javascript:" not in html


class TestFormattingPreserved:
    def test_markdown_constructs_still_render(self):
        html = _md_to_html(
            "# H1\n\n## H2\n\n### H3\n\n**bold** and *it*\n\n- item\n\n"
            "[[target|Label]] [[other:id]] [site](https://example.com/?a=1&b=2)",
            "kb",
        )
        for frag in (
            "<h1>H1</h1>",
            "<h2>H2</h2>",
            "<h3>H3</h3>",
            "<strong>bold</strong>",
            "<em>it</em>",
            "<li>item</li>",
            '<a href="/site/kb/target">Label</a>',
            '<a href="/site/other/id">id</a>',
            '<a href="https://example.com/?a=1&amp;b=2">site</a>',
        ):
            assert frag in html, frag

    def test_inline_link_and_bold(self):
        out = _md_inline("**b** [x](https://e.com) <i>")
        assert "<strong>b</strong>" in out
        assert '<a href="https://e.com">x</a>' in out
        assert "&lt;i&gt;" in out

    def test_javascript_link_blocked_even_when_entity_encoded(self):
        out = _md_to_html("[x](jav&#x61;script:alert(1)) [y](&#106;avascript:alert(2))", "kb")
        assert "<a " not in out


class TestSiteSecurityHeaders:
    def test_site_pages_send_csp_and_nosniff(self, env, monkeypatch):
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        monkeypatch.setenv("PYRITE_DATA_DIR", str(env["tmp"]))
        _put(env["db"], "ok", body="fine")
        env["svc"].render_all()
        client = TestClient(create_app(config=env["config"]))
        for path in ("/site", f"/site/{KB}", f"/site/{KB}/ok", "/site/search"):
            r = client.get(path)
            assert r.status_code == 200, path
            csp = r.headers.get("content-security-policy", "")
            assert "default-src 'self'" in csp, (path, csp)
            assert "script-src 'self'" in csp, (path, csp)
            assert "unsafe-inline" not in csp.split("script-src", 1)[1].split(";")[0], csp
            assert r.headers.get("x-content-type-options") == "nosniff", path

    def test_page_scripts_served_from_static_route(self, env, monkeypatch):
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        monkeypatch.setenv("PYRITE_DATA_DIR", str(env["tmp"]))
        client = TestClient(create_app(config=env["config"]))
        for name in ("site.js", "site-search.js"):
            r = client.get(f"/site/_static/{name}")
            assert r.status_code == 200, name
            assert r.headers["content-type"].startswith("text/javascript")
            assert r.headers.get("x-content-type-options") == "nosniff"
        # Only those two files: not the templates beside them.
        assert client.get("/site/_static/base.html").status_code == 404

    def test_rendered_pages_have_no_inline_script_or_handlers(self, env):
        """Under `script-src 'self'` an inline script would be dead code."""
        _put(env["db"], "ok", body="fine")
        _put(env["db"], "_homepage", title="Home", body="## Explore\n\n[A](/x) — a card\n")
        env["svc"].render_all()
        for page in (env["cache"] / "index.html", env["cache"] / KB / "ok.html"):
            scan = _Scan()
            scan.feed(page.read_text())
            for attrs, text in scan.scripts:
                if attrs.get("type") == "application/ld+json":
                    continue
                assert attrs.get("src"), f"inline script in {page.name}: {text[:80]}"
            for tag, attrs in scan.tags:
                assert not [k for k in attrs if k.startswith("on")], (page.name, tag, attrs)
        home = (env["cache"] / KB / "index.html").read_text()
        assert "onmouseover" not in home


class TestNoOtherUnescapedHtmlRenderers:
    """Grep-level guard: every module that emits HTML has been reviewed.

    Reviewed for #2 (2026-09-23): services/site_cache.py (escaped),
    server/static.py (serves cached files, no entry fields),
    server/static_search_page.py (fixed string; results escaped client
    side), github_auth.py (fixed strings). renderers/ emit Markdown and
    YAML for Quartz and NotebookLM, not HTML the server serves.
    A new module here must be reviewed and added.
    """

    REVIEWED = {
        "pyrite/services/site_cache.py",
        "pyrite/server/static.py",
        "pyrite/server/static_search_page.py",
        "pyrite/github_auth.py",
    }

    def test_html_emitters_are_the_reviewed_set(self):
        root = Path(__file__).resolve().parent.parent
        pattern = re.compile(r"HTMLResponse|text/html|<html|<div[ >]|<a href=")
        found = {
            str(p.relative_to(root))
            for p in (root / "pyrite").rglob("*.py")
            if pattern.search(p.read_text(encoding="utf-8"))
        }
        assert found == self.REVIEWED

    def test_site_cache_never_embeds_raw_json_dumps_in_script(self):
        src = (Path(__file__).resolve().parent.parent / "pyrite/services/site_cache.py").read_text()
        assert "{json.dumps(" not in src


class TestOperatorCspExtension:
    """Operators whose reverse proxy injects a script (deploy/demo/Caddyfile
    adds Plausible) extend the /site policy with `site_csp_extra`."""

    EXTRA = "script-src https://plausible.io 'sha256-abc='; connect-src https://plausible.io"

    def _client(self, env, monkeypatch, extra):
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        monkeypatch.setenv("PYRITE_DATA_DIR", str(env["tmp"]))
        env["config"].settings.site_csp_extra = extra
        _put(env["db"], "ok", body="fine")
        env["svc"].render_all()
        return TestClient(create_app(config=env["config"]))

    def test_extra_sources_appended_to_directives(self, env, monkeypatch):
        client = self._client(env, monkeypatch, self.EXTRA)
        for path in ("/site", f"/site/{KB}/ok", "/site/search", "/site/no-such-kb/x"):
            csp = client.get(path).headers["content-security-policy"]
            directives = {d.split()[0]: d.split()[1:] for d in csp.split(";") if d.strip()}
            assert directives["script-src"] == ["'self'", "https://plausible.io", "'sha256-abc='"]
            assert directives["connect-src"] == ["'self'", "https://plausible.io"]
            assert directives["object-src"] == ["'none'"], path

    def test_new_directive_is_added(self, env, monkeypatch):
        client = self._client(env, monkeypatch, "worker-src 'none'")
        csp = client.get(f"/site/{KB}/ok").headers["content-security-policy"]
        assert "worker-src 'none'" in csp
        assert "script-src 'self';" in csp

    @pytest.mark.parametrize(
        "bad",
        [
            "script-src https://a.example\r\nX-Evil: 1",
            "script-src https://a.example, default-src *",
            "Script_Src https://a.example",
        ],
    )
    def test_malformed_extra_is_ignored(self, env, monkeypatch, bad):
        client = self._client(env, monkeypatch, bad)
        r = client.get(f"/site/{KB}/ok")
        assert r.status_code == 200
        assert "a.example" not in r.headers["content-security-policy"]
        assert "x-evil" not in r.headers

    def test_setting_loads_from_yaml_and_env(self, monkeypatch):
        from pyrite.config import _apply_env_overrides

        cfg = PyriteConfig.from_dict({"settings": {"site_csp_extra": self.EXTRA}})
        assert cfg.settings.site_csp_extra == self.EXTRA
        assert cfg.to_dict()["settings"]["site_csp_extra"] == self.EXTRA
        monkeypatch.setenv("PYRITE_SITE_CSP_EXTRA", "connect-src https://x.example")
        _apply_env_overrides(cfg)
        assert cfg.settings.site_csp_extra == "connect-src https://x.example"
        assert Settings(index_path="x").site_csp_extra == ""

    def test_demo_caddyfile_hash_matches_its_injected_script(self):
        """The Caddyfile comment tells the operator which hash to allow;
        it must be the hash of the inline script the proxy injects."""
        import base64
        import hashlib

        caddy = (Path(__file__).resolve().parent.parent / "deploy/demo/Caddyfile").read_text()
        inline = re.search(r"<script>(.*?)</script>", caddy).group(1)
        digest = base64.b64encode(hashlib.sha256(inline.encode()).digest()).decode()
        assert f"'sha256-{digest}'" in caddy


class TestCspExtraGuardrails:
    """`site_csp_extra` can widen the policy, but not where widening defeats it."""

    @staticmethod
    def _build(extra):
        from pyrite.server.static import build_site_csp

        build_site_csp.cache_clear()  # warnings are logged once per value
        csp = build_site_csp(extra)
        return {d.split()[0]: d.split()[1:] for d in csp.split(";") if d.strip()}

    @pytest.mark.parametrize("directive", ["object-src", "base-uri"])
    def test_object_src_and_base_uri_cannot_be_extended(self, directive, caplog):
        with caplog.at_level("WARNING", logger="pyrite.server.static"):
            d = self._build(f"{directive} https://evil.example")
        assert "https://evil.example" not in d[directive]
        assert d[directive] == (["'none'"] if directive == "object-src" else ["'self'"])
        assert directive in caplog.text

    @pytest.mark.parametrize("directive", ["script-src", "default-src"])
    @pytest.mark.parametrize("source", ["'unsafe-inline'", "'unsafe-eval'", "*"])
    def test_weakening_script_sources_is_warned(self, directive, source, caplog):
        with caplog.at_level("WARNING", logger="pyrite.server.static"):
            d = self._build(f"{directive} {source}")
        assert source in d[directive]  # the operator's call, but loudly
        assert source in caplog.text
        assert directive in caplog.text

    def test_ordinary_source_is_not_warned(self, caplog):
        with caplog.at_level("WARNING", logger="pyrite.server.static"):
            self._build("script-src https://plausible.io")
        assert caplog.text == ""

    @pytest.mark.parametrize("directive", ["upgrade-insecure-requests", "block-all-mixed-content"])
    def test_valueless_directive_is_accepted(self, directive, caplog):
        with caplog.at_level("WARNING", logger="pyrite.server.static"):
            d = self._build(f"{directive}; connect-src https://x.example")
        assert d[directive] == []
        assert d["connect-src"] == ["'self'", "https://x.example"]
        assert "malformed" not in caplog.text
