"""``POST /api/index/sync?wait=true`` actually re-renders the site cache (#349).

Same root cause as #326/#322: the sync handler is a plain ``def`` route, so
it runs on a worker thread with no running event loop. The old code called
``asyncio.get_running_loop()`` from there, which raises, and a broad
``except Exception`` swallowed it -- so the site cache was never rendered.
A second, independent bug hid behind the first: the guard that was supposed
to skip the render when unconfigured (``if cache_svc.config:``) read
``request.app.state.config``, which nothing in the server ever sets, so it
was always ``None`` and the render never even reached the loop lookup.

**Surface.** A ``TestClient`` used as a context manager, so the app's
lifespan runs (startup binds the loop -- #326's ``bind_loop``/``_loop`` --
even though this fix does not need it, since the render happens
synchronously while the caller is already waiting). A markdown file is
written directly into the KB path (mirroring an external edit, exactly like
``tests/test_integration.py::test_manual_file_creation_syncs``) so
``sync_incremental`` reports a real ``added`` count, then
``POST /api/index/sync?wait=true`` is called and the rendered site-cache
file is checked on disk.

The KB is created with ``default_role="read"``: since the security-batch-2
change, ``/site`` (and ``SiteCacheService.render_all``) renders only public
KBs (``public_kbs.public_kb_names``); a KB with no default role renders
nothing, which would pass this test for the wrong reason.
"""

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient  # noqa: E402

from pyrite.config import KBConfig, PyriteConfig, Settings  # noqa: E402
from pyrite.server.api import create_app  # noqa: E402


def _config(tmp_path: Path) -> PyriteConfig:
    kb_path = tmp_path / "public-kb"
    kb_path.mkdir()
    return PyriteConfig(
        knowledge_bases=[
            KBConfig(name="public-kb", path=kb_path, kb_type="generic", default_role="read"),
        ],
        settings=Settings(index_path=tmp_path / "index.db"),
    )


def _write_entry(kb_path: Path) -> None:
    (kb_path / "manual-entry.md").write_text(
        """---
id: manual-entry
title: Manually Created Entry
entry_type: note
---

This entry was added directly to disk, the way an external edit would be.
"""
    )


class TestSyncWaitRerendersSiteCache:
    def test_sync_wait_true_rerenders_site_cache(self, tmp_path):
        config = _config(tmp_path)
        app = create_app(config=config)

        _write_entry(config.get_kb("public-kb").path)

        # SiteCacheService derives cache_dir from index_path's parent.
        expected_cache_dir = config.settings.index_path.parent / "site-cache"

        with TestClient(app) as client:
            resp = client.post("/api/index/sync", params={"wait": "true"})
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["added"] == 1, (
                f"precondition: sync should have picked up the manually written file, got {body}"
            )

        landing = expected_cache_dir / "index.html"
        assert landing.exists(), (
            "the site cache was never rendered after a sync that added an "
            f"entry (looked for {landing})"
        )
        html = landing.read_text()
        assert "public-kb" in html

    def test_sync_wait_true_does_not_hide_a_real_render_failure(self, tmp_path, monkeypatch):
        """No broad ``except`` may swallow a real rendering failure.

        Acceptance criterion, verbatim: "no broad `except` hiding the
        failure." If ``render_all`` raises, that exception must propagate
        (or otherwise fail the request) rather than being logged away.
        """
        import pyrite.services.site_cache as site_cache_module

        config = _config(tmp_path)
        app = create_app(config=config)
        _write_entry(config.get_kb("public-kb").path)

        def _boom(self):
            raise RuntimeError("boom: rendering exploded")

        monkeypatch.setattr(site_cache_module.SiteCacheService, "render_all", _boom)

        with TestClient(app) as client, pytest.raises(Exception, match="boom"):
            client.post("/api/index/sync", params={"wait": "true"})
