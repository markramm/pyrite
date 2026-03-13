"""Tests for URL liveness checking service."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyrite.config import PyriteConfig, Settings, KBConfig
from pyrite.storage.database import PyriteDB
from pyrite.services.kb_service import KBService
from pyrite.services.url_checker import URLChecker, URLCheckResult


@pytest.fixture
def setup(tmp_path):
    """Set up a KB with entries that have source URLs."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    kb = KBConfig(name="test", path=kb_path, kb_type="cascade-timeline")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    svc = KBService(config, db)

    svc.create_entry(
        "test", "e1", "Event 1", "timeline_event",
        date="2025-01-01",
        sources=[
            {"title": "Good Source", "url": "https://example.com/good"},
            {"title": "Bad Source", "url": "https://example.com/404"},
        ],
    )
    svc.create_entry(
        "test", "e2", "Event 2", "timeline_event",
        date="2025-02-01",
        sources=[
            {"title": "Another", "url": "https://example.com/good"},
        ],
    )
    svc.create_entry(
        "test", "e3", "No sources", "timeline_event",
        date="2025-03-01",
    )

    yield {"db": db, "svc": svc, "config": config, "tmp_path": tmp_path}
    db.close()


class TestURLExtraction:
    """Test extracting URLs from KB entries."""

    def test_collects_urls(self, setup):
        checker = URLChecker(setup["db"])
        urls = checker.collect_urls("test")
        # example.com/good appears in 2 entries, /404 in 1
        assert "https://example.com/good" in urls
        assert "https://example.com/404" in urls
        assert len(urls["https://example.com/good"]) == 2  # 2 entries use this URL

    def test_skips_empty_urls(self, setup):
        checker = URLChecker(setup["db"])
        urls = checker.collect_urls("test")
        # Should not have empty or None URLs
        assert "" not in urls
        assert None not in urls


class TestURLCheckResult:
    """Test the URLCheckResult dataclass."""

    def test_ok_result(self):
        r = URLCheckResult(url="https://example.com", status_code=200, ok=True)
        assert r.ok
        assert r.status_code == 200

    def test_broken_result(self):
        r = URLCheckResult(url="https://example.com/404", status_code=404, ok=False)
        assert not r.ok

    def test_error_result(self):
        r = URLCheckResult(url="https://example.com", status_code=0, ok=False, error="timeout")
        assert not r.ok
        assert r.error == "timeout"


class TestURLChecker:
    """Test URL checking logic (with mocked HTTP)."""

    def test_check_urls_with_mock(self, setup):
        checker = URLChecker(setup["db"])
        urls = checker.collect_urls("test")

        # Mock the actual HTTP checking
        def mock_check(url):
            if "404" in url:
                return URLCheckResult(url=url, status_code=404, ok=False)
            return URLCheckResult(url=url, status_code=200, ok=True)

        results = [mock_check(url) for url in urls]
        ok = [r for r in results if r.ok]
        broken = [r for r in results if not r.ok]
        assert len(ok) == 1
        assert len(broken) == 1

    def test_report_structure(self, setup):
        checker = URLChecker(setup["db"])
        urls = checker.collect_urls("test")

        report = checker.build_report(
            urls,
            [
                URLCheckResult(url="https://example.com/good", status_code=200, ok=True),
                URLCheckResult(url="https://example.com/404", status_code=404, ok=False),
            ],
        )
        assert report["total_urls"] == 2
        assert report["ok"] == 1
        assert report["broken"] == 1
        # Broken entries should list the entry IDs that reference them
        broken_entry = report["broken_details"][0]
        assert broken_entry["url"] == "https://example.com/404"
        assert "e1" in broken_entry["entry_ids"]

    def test_cache_saves_and_loads(self, setup):
        cache_path = setup["tmp_path"] / "url_cache.json"
        checker = URLChecker(setup["db"], cache_path=cache_path)

        result = URLCheckResult(url="https://example.com/good", status_code=200, ok=True)
        checker.save_cache({"https://example.com/good": result})

        loaded = checker.load_cache()
        assert "https://example.com/good" in loaded
        assert loaded["https://example.com/good"].ok
