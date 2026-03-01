"""Tests for block extraction, block migration v5, and block CRUD operations."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB
from pyrite.storage.migrations import CURRENT_VERSION, MIGRATIONS, MigrationManager
from pyrite.utils.markdown_blocks import extract_blocks

# =========================================================================
# Block Extraction Tests
# =========================================================================


class TestMarkdownBlockExtraction:
    """Tests for markdown_blocks.extract_blocks()."""

    def test_heading_extraction(self):
        """Headings h1-h6 are extracted as heading blocks."""
        md = "# H1\n\n## H2\n\n### H3\n\n#### H4\n\n##### H5\n\n###### H6"
        blocks = extract_blocks(md)
        headings = [b for b in blocks if b["block_type"] == "heading"]
        assert len(headings) == 6
        assert headings[0]["content"] == "# H1"
        assert headings[0]["heading"] == "H1"
        assert headings[5]["content"] == "###### H6"
        assert headings[5]["heading"] == "H6"

    def test_paragraph_extraction(self):
        """Plain text paragraphs are extracted."""
        md = "This is a paragraph.\n\nThis is another paragraph."
        blocks = extract_blocks(md)
        assert len(blocks) == 2
        assert all(b["block_type"] == "paragraph" for b in blocks)
        assert blocks[0]["content"] == "This is a paragraph."
        assert blocks[1]["content"] == "This is another paragraph."

    def test_code_block_extraction(self):
        """Fenced code blocks are extracted."""
        md = "```python\ndef hello():\n    print('hi')\n```"
        blocks = extract_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["block_type"] == "code"
        assert "def hello():" in blocks[0]["content"]
        assert blocks[0]["content"].startswith("```python")
        assert blocks[0]["content"].endswith("```")

    def test_list_extraction_bulleted(self):
        """Bulleted lists are extracted as list blocks."""
        md = "- item 1\n- item 2\n- item 3"
        blocks = extract_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["block_type"] == "list"
        assert "item 1" in blocks[0]["content"]
        assert "item 3" in blocks[0]["content"]

    def test_list_extraction_numbered(self):
        """Numbered lists are extracted as list blocks."""
        md = "1. first\n2. second\n3. third"
        blocks = extract_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["block_type"] == "list"
        assert "first" in blocks[0]["content"]

    def test_block_id_generation(self):
        """Block IDs are 8-char hex strings from SHA-256."""
        md = "Hello world"
        blocks = extract_blocks(md)
        assert len(blocks) == 1
        block_id = blocks[0]["block_id"]
        assert len(block_id) == 8
        # Should be hex
        int(block_id, 16)

    def test_block_id_deterministic(self):
        """Same content produces same block ID."""
        md = "Hello world"
        blocks1 = extract_blocks(md)
        blocks2 = extract_blocks(md)
        assert blocks1[0]["block_id"] == blocks2[0]["block_id"]

    def test_explicit_block_id_marker(self):
        """Explicit ^block-id markers override auto-generated IDs."""
        md = "This is a paragraph.\n^my-custom-id"
        blocks = extract_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["block_id"] == "my-custom-id"

    def test_heading_context_tracking(self):
        """Paragraphs under headings track their heading context."""
        md = "# Introduction\n\nSome intro text.\n\n## Details\n\nSome detail text."
        blocks = extract_blocks(md)
        assert len(blocks) == 4
        # Heading block itself has its own heading
        assert blocks[0]["heading"] == "Introduction"
        assert blocks[0]["block_type"] == "heading"
        # Paragraph under Introduction
        assert blocks[1]["heading"] == "Introduction"
        assert blocks[1]["block_type"] == "paragraph"
        # Details heading
        assert blocks[2]["heading"] == "Details"
        assert blocks[2]["block_type"] == "heading"
        # Paragraph under Details
        assert blocks[3]["heading"] == "Details"
        assert blocks[3]["block_type"] == "paragraph"

    def test_no_heading_context_before_first_heading(self):
        """Blocks before any heading have heading=None."""
        md = "First paragraph.\n\n# Title\n\nSecond paragraph."
        blocks = extract_blocks(md)
        assert blocks[0]["heading"] is None
        assert blocks[0]["block_type"] == "paragraph"
        assert blocks[1]["heading"] == "Title"

    def test_empty_input(self):
        """Empty or whitespace-only input returns no blocks."""
        assert extract_blocks("") == []
        assert extract_blocks("   \n\n  ") == []
        assert extract_blocks(None) == []

    def test_position_tracking(self):
        """Blocks have sequential 0-based positions."""
        md = "# Heading\n\nParagraph\n\n- list item"
        blocks = extract_blocks(md)
        positions = [b["position"] for b in blocks]
        assert positions == [0, 1, 2]

    def test_mixed_content(self):
        """Mixed content types are all extracted correctly."""
        md = (
            "# Title\n\n"
            "A paragraph.\n\n"
            "- item 1\n- item 2\n\n"
            "```\ncode here\n```\n\n"
            "Another paragraph."
        )
        blocks = extract_blocks(md)
        types = [b["block_type"] for b in blocks]
        assert types == ["heading", "paragraph", "list", "code", "paragraph"]

    def test_multiline_paragraph(self):
        """Multi-line paragraph without blank lines stays together."""
        md = "Line one\nLine two\nLine three"
        blocks = extract_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["block_type"] == "paragraph"
        assert "Line one\nLine two\nLine three" == blocks[0]["content"]


# =========================================================================
# Migration Tests
# =========================================================================


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
    db_path.unlink()


class TestBlockMigration:
    """Tests for migration v5 (block table)."""

    def test_migration_v5_exists(self):
        """Migration v5 for block references exists."""
        v5 = [m for m in MIGRATIONS if m.version == 5]
        assert len(v5) == 1
        assert "block" in v5[0].description.lower()

    def test_current_version_is_5(self):
        """CURRENT_VERSION is 5."""
        assert CURRENT_VERSION == 5

    def test_migration_v5_creates_block_table(self, temp_db):
        """Migration v5 creates the block table."""
        # Need baseline tables for foreign keys
        temp_db.execute("""
            CREATE TABLE IF NOT EXISTS kb (
                name TEXT PRIMARY KEY,
                kb_type TEXT NOT NULL,
                path TEXT NOT NULL,
                description TEXT,
                last_indexed TEXT,
                entry_count INTEGER DEFAULT 0,
                repo_id INTEGER,
                repo_subpath TEXT DEFAULT ''
            )
        """)
        temp_db.execute("""
            CREATE TABLE IF NOT EXISTS entry (
                id TEXT NOT NULL,
                kb_name TEXT NOT NULL REFERENCES kb(name) ON DELETE CASCADE,
                entry_type TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT,
                summary TEXT,
                file_path TEXT,
                date TEXT,
                importance INTEGER,
                status TEXT,
                location TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT,
                indexed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                modified_by TEXT,
                PRIMARY KEY (id, kb_name)
            )
        """)
        temp_db.commit()

        mgr = MigrationManager(temp_db)
        # Apply only v5
        v5 = [m for m in MIGRATIONS if m.version == 5][0]
        mgr._apply_migration(v5)

        # Verify table exists
        row = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='block'"
        ).fetchone()
        assert row is not None

        # Verify columns
        cols = temp_db.execute("PRAGMA table_info(block)").fetchall()
        col_names = {c["name"] for c in cols}
        assert col_names == {
            "id", "entry_id", "kb_name", "block_id",
            "heading", "content", "position", "block_type",
        }

    def test_migration_v5_has_rollback(self):
        """Migration v5 has rollback SQL."""
        v5 = [m for m in MIGRATIONS if m.version == 5][0]
        assert "DROP TABLE" in v5.down


# =========================================================================
# CRUD Tests
# =========================================================================


@pytest.fixture
def db():
    """Fresh PyriteDB with a registered KB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = PyriteDB(Path(tmpdir) / "test.db")
        db.register_kb("test", "generic", "/tmp/test")
        yield db
        db.close()


def _make_entry(entry_id="e1", **overrides):
    """Helper to build entry data dict."""
    data = {
        "id": entry_id,
        "kb_name": "test",
        "entry_type": "note",
        "title": f"Title {entry_id}",
        "body": f"Body for {entry_id}",
        "tags": [],
        "sources": [],
        "links": [],
    }
    data.update(overrides)
    return data


class TestBlockCRUD:
    """Tests for block sync during upsert_entry."""

    def test_upsert_creates_blocks(self, db):
        """Upserting an entry with _blocks creates block rows."""
        blocks = [
            {
                "block_id": "abc12345",
                "heading": "Intro",
                "content": "# Intro",
                "position": 0,
                "block_type": "heading",
            },
            {
                "block_id": "def67890",
                "heading": "Intro",
                "content": "Some text here.",
                "position": 1,
                "block_type": "paragraph",
            },
        ]
        db.upsert_entry(_make_entry("b1", _blocks=blocks))

        # Query blocks directly via raw SQL
        rows = db._raw_conn.execute(
            "SELECT block_id, heading, content, position, block_type "
            "FROM block WHERE entry_id = 'b1' AND kb_name = 'test' "
            "ORDER BY position"
        ).fetchall()
        assert len(rows) == 2
        assert rows[0][0] == "abc12345"
        assert rows[0][1] == "Intro"
        assert rows[0][4] == "heading"
        assert rows[1][0] == "def67890"
        assert rows[1][3] == 1

    def test_re_upsert_replaces_blocks(self, db):
        """Re-upserting an entry replaces its blocks."""
        blocks_v1 = [
            {
                "block_id": "aaa11111",
                "heading": None,
                "content": "Old content",
                "position": 0,
                "block_type": "paragraph",
            },
        ]
        blocks_v2 = [
            {
                "block_id": "bbb22222",
                "heading": "New",
                "content": "New content",
                "position": 0,
                "block_type": "paragraph",
            },
            {
                "block_id": "ccc33333",
                "heading": "New",
                "content": "More new content",
                "position": 1,
                "block_type": "paragraph",
            },
        ]
        db.upsert_entry(_make_entry("b2", _blocks=blocks_v1))
        db.upsert_entry(_make_entry("b2", _blocks=blocks_v2))

        rows = db._raw_conn.execute(
            "SELECT block_id FROM block WHERE entry_id = 'b2' AND kb_name = 'test' "
            "ORDER BY position"
        ).fetchall()
        assert len(rows) == 2
        assert rows[0][0] == "bbb22222"
        assert rows[1][0] == "ccc33333"

    def test_upsert_without_blocks(self, db):
        """Upserting without _blocks doesn't create block rows."""
        db.upsert_entry(_make_entry("b3"))
        rows = db._raw_conn.execute(
            "SELECT COUNT(*) FROM block WHERE entry_id = 'b3' AND kb_name = 'test'"
        ).fetchone()
        assert rows[0] == 0

    def test_delete_entry_cascades_blocks(self, db):
        """Deleting an entry removes its blocks."""
        blocks = [
            {
                "block_id": "del12345",
                "heading": None,
                "content": "Will be deleted",
                "position": 0,
                "block_type": "paragraph",
            },
        ]
        db.upsert_entry(_make_entry("b4", _blocks=blocks))
        db.delete_entry("b4", "test")

        rows = db._raw_conn.execute(
            "SELECT COUNT(*) FROM block WHERE entry_id = 'b4' AND kb_name = 'test'"
        ).fetchone()
        assert rows[0] == 0
