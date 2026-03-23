"""Tests for edge endpoint sync in the index pipeline."""

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB


@pytest.fixture
def db_with_entry(tmp_path):
    """DB with entries for edge endpoint testing."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    kb = KBConfig(name="test", path=kb_path, kb_type="standard")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    db.register_kb("test", "standard", str(kb_path))

    # Create entries that will be endpoints
    db.upsert_entry(
        {
            "id": "person-1",
            "kb_name": "test",
            "title": "Person 1",
            "entry_type": "person",
        }
    )
    db.upsert_entry(
        {
            "id": "company-1",
            "kb_name": "test",
            "title": "Company 1",
            "entry_type": "organization",
        }
    )

    yield db
    db.close()


class TestSyncEdgeEndpoints:
    """Tests for _sync_edge_endpoints in SQLiteBackend."""

    def test_sync_edge_endpoints_populates_table(self, db_with_entry):
        """Upserting with _edge_endpoints creates rows in edge_endpoint table."""
        db_with_entry.upsert_entry(
            {
                "id": "employment-1",
                "kb_name": "test",
                "title": "Employment Edge",
                "entry_type": "employment",
                "_edge_endpoints": [
                    {
                        "role": "source",
                        "field_name": "employee",
                        "endpoint_id": "person-1",
                        "endpoint_kb": "test",
                        "edge_type": "employment",
                    },
                    {
                        "role": "target",
                        "field_name": "employer",
                        "endpoint_id": "company-1",
                        "endpoint_kb": "test",
                        "edge_type": "employment",
                    },
                ],
            }
        )
        rows = db_with_entry._raw_conn.execute(
            "SELECT * FROM edge_endpoint WHERE edge_entry_id = ? AND edge_entry_kb = ?",
            ("employment-1", "test"),
        ).fetchall()
        assert len(rows) == 2
        roles = {r[3] for r in rows}  # role column
        assert roles == {"source", "target"}

    def test_sync_edge_endpoints_clears_on_update(self, db_with_entry):
        """Re-upserting replaces old endpoints with new ones."""
        db_with_entry.upsert_entry(
            {
                "id": "employment-1",
                "kb_name": "test",
                "title": "Employment Edge",
                "entry_type": "employment",
                "_edge_endpoints": [
                    {
                        "role": "source",
                        "field_name": "employee",
                        "endpoint_id": "person-1",
                        "endpoint_kb": "test",
                        "edge_type": "employment",
                    },
                ],
            }
        )
        rows = db_with_entry._raw_conn.execute(
            "SELECT * FROM edge_endpoint WHERE edge_entry_id = ? AND edge_entry_kb = ?",
            ("employment-1", "test"),
        ).fetchall()
        assert len(rows) == 1

        # Update with different endpoint
        db_with_entry.upsert_entry(
            {
                "id": "employment-1",
                "kb_name": "test",
                "title": "Employment Edge",
                "entry_type": "employment",
                "_edge_endpoints": [
                    {
                        "role": "target",
                        "field_name": "employer",
                        "endpoint_id": "company-1",
                        "endpoint_kb": "test",
                        "edge_type": "employment",
                    },
                ],
            }
        )
        rows = db_with_entry._raw_conn.execute(
            "SELECT * FROM edge_endpoint WHERE edge_entry_id = ? AND edge_entry_kb = ?",
            ("employment-1", "test"),
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][3] == "target"  # role column
        assert rows[0][5] == "company-1"  # endpoint_id column

    def test_sync_edge_endpoints_empty_list(self, db_with_entry):
        """Upserting with empty _edge_endpoints creates no rows."""
        db_with_entry.upsert_entry(
            {
                "id": "employment-1",
                "kb_name": "test",
                "title": "Employment Edge",
                "entry_type": "employment",
                "_edge_endpoints": [],
            }
        )
        rows = db_with_entry._raw_conn.execute(
            "SELECT * FROM edge_endpoint WHERE edge_entry_id = ? AND edge_entry_kb = ?",
            ("employment-1", "test"),
        ).fetchall()
        assert len(rows) == 0

    def test_sync_edge_endpoints_no_key(self, db_with_entry):
        """Upserting without _edge_endpoints key causes no error and no rows."""
        db_with_entry.upsert_entry(
            {
                "id": "employment-1",
                "kb_name": "test",
                "title": "Employment Edge",
                "entry_type": "employment",
            }
        )
        rows = db_with_entry._raw_conn.execute(
            "SELECT * FROM edge_endpoint WHERE edge_entry_id = ? AND edge_entry_kb = ?",
            ("employment-1", "test"),
        ).fetchall()
        assert len(rows) == 0

    def test_upsert_entry_includes_edge_endpoints(self, db_with_entry):
        """Full integration: upsert populates edge_endpoint table via raw SQL."""
        endpoints = [
            {
                "role": "source",
                "field_name": "owner",
                "endpoint_id": "person-1",
                "endpoint_kb": "test",
                "edge_type": "ownership",
            },
            {
                "role": "target",
                "field_name": "asset",
                "endpoint_id": "company-1",
                "endpoint_kb": "test",
                "edge_type": "ownership",
            },
        ]
        db_with_entry.upsert_entry(
            {
                "id": "ownership-1",
                "kb_name": "test",
                "title": "Ownership Edge",
                "entry_type": "ownership",
                "_edge_endpoints": endpoints,
            }
        )
        rows = db_with_entry._raw_conn.execute(
            "SELECT edge_entry_id, edge_entry_kb, role, field_name, endpoint_id, endpoint_kb, edge_type "
            "FROM edge_endpoint WHERE edge_entry_id = ? AND edge_entry_kb = ?",
            ("ownership-1", "test"),
        ).fetchall()
        assert len(rows) == 2
        by_role = {r[2]: r for r in rows}
        assert by_role["source"][4] == "person-1"  # endpoint_id
        assert by_role["target"][4] == "company-1"


class TestIndexManagerEdgeEndpointExtraction:
    """Test _entry_to_dict extracts edge endpoints from schema."""

    def test_index_manager_extracts_edge_endpoints(self, tmp_path):
        """_entry_to_dict populates _edge_endpoints when type has edge_type=True."""
        from unittest.mock import MagicMock, PropertyMock

        from pyrite.config import KBConfig, PyriteConfig, Settings
        from pyrite.storage.index import IndexManager

        kb_path = tmp_path / "test-kb"
        kb_path.mkdir()
        kb = KBConfig(name="test", path=kb_path, kb_type="standard")
        config = PyriteConfig(
            knowledge_bases=[kb],
            settings=Settings(index_path=tmp_path / "index.db"),
        )
        index_mgr = IndexManager(config)

        # Mock entry
        entry = MagicMock()
        entry.id = "ownership-1"
        entry.entry_type = "ownership"
        entry.title = "Ownership Edge"
        entry.body = ""
        entry.summary = None
        entry.file_path = "ownership-1.md"
        entry.date = None
        entry.importance = None
        entry.status = None
        entry.tags = []
        entry.sources = []
        entry.links = []
        entry.metadata = {}
        entry.to_frontmatter.return_value = {
            "owner": "person-1",
            "asset": "[[company-1]]",
        }

        # Mock schema with edge_type
        mock_endpoint_source = MagicMock()
        mock_endpoint_source.field = "owner"
        mock_endpoint_target = MagicMock()
        mock_endpoint_target.field = "asset"

        mock_type_schema = MagicMock()
        mock_type_schema.edge_type = True
        mock_type_schema.endpoints = {
            "source": mock_endpoint_source,
            "target": mock_endpoint_target,
        }
        mock_type_schema.fields = {}

        mock_schema = MagicMock()
        mock_schema.types = {"ownership": mock_type_schema}

        mock_kb_config = MagicMock()
        mock_kb_config.kb_yaml_path.exists.return_value = True
        type(mock_kb_config).kb_schema = PropertyMock(return_value=mock_schema)

        # Patch config.get_kb to return our mock
        index_mgr.config = MagicMock()
        index_mgr.config.get_kb.return_value = mock_kb_config

        result = index_mgr._entry_to_dict(entry, "test", kb_path / "ownership-1.md")

        assert "_edge_endpoints" in result
        eps = result["_edge_endpoints"]
        assert len(eps) == 2
        by_role = {ep["role"]: ep for ep in eps}
        assert by_role["source"]["endpoint_id"] == "person-1"
        assert by_role["source"]["field_name"] == "owner"
        assert by_role["target"]["endpoint_id"] == "company-1"  # brackets stripped
        assert by_role["target"]["field_name"] == "asset"
        assert by_role["source"]["edge_type"] == "ownership"
