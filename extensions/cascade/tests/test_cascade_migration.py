"""Tests for Cascade Series migration scripts."""

import textwrap

import pytest
from pyrite_cascade.migration import (
    inject_ids,
    normalize_research_frontmatter,
    normalize_timeline_frontmatter,
    normalize_wikilinks,
)


@pytest.fixture
def tmp_kb(tmp_path):
    """Create a temporary KB directory with sample files."""
    return tmp_path


def _write_md(path, content):
    """Write a markdown file with dedented content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


# ---------------------------------------------------------------------------
# inject_ids
# ---------------------------------------------------------------------------


class TestInjectIds:
    def test_adds_id_from_filename(self, tmp_kb):
        _write_md(
            tmp_kb / "actors" / "powell-lewis.md",
            """\
            ---
            title: "Lewis Powell"
            type: actor
            ---
            Body text.
            """,
        )
        result = inject_ids(tmp_kb)
        assert len(result) == 1

        content = (tmp_kb / "actors" / "powell-lewis.md").read_text()
        assert "id: powell-lewis" in content

    def test_skips_existing_id(self, tmp_kb):
        _write_md(
            tmp_kb / "actors" / "trump.md",
            """\
            ---
            id: trump-donald
            title: "Donald Trump"
            type: actor
            ---
            Body.
            """,
        )
        result = inject_ids(tmp_kb)
        assert len(result) == 0

    def test_skips_index_files(self, tmp_kb):
        _write_md(tmp_kb / "_index.md", "---\ntitle: Index\n---\n")
        result = inject_ids(tmp_kb)
        assert len(result) == 0

    def test_detects_id_collisions(self, tmp_kb, capsys):
        _write_md(
            tmp_kb / "actors" / "smith.md",
            "---\ntitle: Actor Smith\ntype: actor\n---\n",
        )
        _write_md(
            tmp_kb / "orgs" / "smith.md",
            "---\ntitle: Org Smith\ntype: organization\n---\n",
        )
        inject_ids(tmp_kb)
        captured = capsys.readouterr()
        assert "collision" in captured.out.lower()


# ---------------------------------------------------------------------------
# normalize_wikilinks
# ---------------------------------------------------------------------------


class TestNormalizeWikilinks:
    def test_strips_folder_prefix(self, tmp_kb):
        _write_md(
            tmp_kb / "orgs" / "heritage.md",
            """\
            ---
            title: Heritage
            ---
            See [[actors/powell-lewis]] and [[organizations/ALEC]].
            """,
        )
        count = normalize_wikilinks(tmp_kb)
        assert count == 2
        content = (tmp_kb / "orgs" / "heritage.md").read_text()
        assert "[[powell-lewis]]" in content
        assert "[[ALEC]]" in content
        assert "actors/" not in content

    def test_preserves_non_prefixed_wikilinks(self, tmp_kb):
        _write_md(
            tmp_kb / "test.md",
            "---\ntitle: Test\n---\nSee [[powell-lewis]] here.\n",
        )
        count = normalize_wikilinks(tmp_kb)
        assert count == 0

    def test_handles_multiple_on_same_line(self, tmp_kb):
        _write_md(
            tmp_kb / "test.md",
            "---\ntitle: Test\n---\n[[actors/a]] and [[events/b]]\n",
        )
        count = normalize_wikilinks(tmp_kb)
        assert count == 2
        content = (tmp_kb / "test.md").read_text()
        assert "[[a]]" in content
        assert "[[b]]" in content


# ---------------------------------------------------------------------------
# normalize_research_frontmatter
# ---------------------------------------------------------------------------


class TestNormalizeResearchFrontmatter:
    def test_essay_type_to_type(self, tmp_kb):
        _write_md(
            tmp_kb / "mech.md",
            "---\ntitle: Test\nessay_type: mechanism\n---\nBody.\n",
        )
        counts = normalize_research_frontmatter(tmp_kb)
        assert counts["essay_type_to_type"] == 1
        content = (tmp_kb / "mech.md").read_text()
        assert "type: mechanism" in content
        assert "essay_type" not in content

    def test_event_date_to_date(self, tmp_kb):
        _write_md(
            tmp_kb / "event.md",
            "---\ntitle: Test\ntype: event\nevent_date: 2021-01-06\n---\n",
        )
        counts = normalize_research_frontmatter(tmp_kb)
        assert counts["event_date_to_date"] == 1
        content = (tmp_kb / "event.md").read_text()
        assert "date: 2021-01-06" in content

    def test_org_to_cascade_org(self, tmp_kb):
        _write_md(
            tmp_kb / "org.md",
            "---\ntitle: Test\ntype: organization\n---\n",
        )
        counts = normalize_research_frontmatter(tmp_kb)
        assert counts["org_to_cascade_org"] == 1
        content = (tmp_kb / "org.md").read_text()
        assert "type: cascade_org" in content

    def test_research_status_normalized(self, tmp_kb):
        _write_md(
            tmp_kb / "actor.md",
            '---\ntitle: Test\nresearch_status: "in-progress"\n---\n',
        )
        counts = normalize_research_frontmatter(tmp_kb)
        assert counts["research_status_normalized"] == 1
        content = (tmp_kb / "actor.md").read_text()
        assert "research_status: in-progress" in content
        assert '"' not in content.split("research_status")[1].split("\n")[0]

    def test_preserves_date_when_both_exist(self, tmp_kb):
        _write_md(
            tmp_kb / "event.md",
            "---\ntitle: Test\ndate: 2025-01-01\nevent_date: 2021-01-06\n---\n",
        )
        counts = normalize_research_frontmatter(tmp_kb)
        assert counts["event_date_to_date"] == 0
        content = (tmp_kb / "event.md").read_text()
        assert "date: 2025-01-01" in content


# ---------------------------------------------------------------------------
# normalize_timeline_frontmatter
# ---------------------------------------------------------------------------


class TestNormalizeTimelineFrontmatter:
    def test_adds_type(self, tmp_kb):
        _write_md(
            tmp_kb / "event.md",
            "---\nid: test\ntitle: Test Event\ndate: 2022-04-01\n---\nBody.\n",
        )
        counts = normalize_timeline_frontmatter(tmp_kb)
        assert counts["type_added"] == 1
        content = (tmp_kb / "event.md").read_text()
        assert "type: timeline_event" in content

    def test_skips_if_type_exists(self, tmp_kb):
        _write_md(
            tmp_kb / "event.md",
            "---\ntype: timeline_event\ntitle: Test\n---\n",
        )
        counts = normalize_timeline_frontmatter(tmp_kb)
        assert counts["type_added"] == 0

    def test_unquotes_date(self, tmp_kb):
        _write_md(
            tmp_kb / "event.md",
            "---\ntype: timeline_event\ndate: '2024-01-15'\ntitle: Test\n---\n",
        )
        counts = normalize_timeline_frontmatter(tmp_kb)
        assert counts["date_unquoted"] == 1
        content = (tmp_kb / "event.md").read_text()
        assert "date: 2024-01-15" in content
        assert "'" not in content.split("date:")[1].split("\n")[0]

    def test_handles_double_quoted_date(self, tmp_kb):
        _write_md(
            tmp_kb / "event.md",
            '---\ntype: timeline_event\ndate: "2024-01-15"\ntitle: Test\n---\n',
        )
        counts = normalize_timeline_frontmatter(tmp_kb)
        assert counts["date_unquoted"] == 1
