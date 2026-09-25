"""Tests for claim-to-edge promotion feature."""

from dataclasses import dataclass

import pytest
from pyrite_journalism_investigation.promote import promote_claim_to_edge

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB


@dataclass
class FakePluginContext:
    config: PyriteConfig
    db: PyriteDB
    kb_service: KBService
    kb_name: str = "test"
    user: str = "test-user"
    operation: str = "mcp"


@pytest.fixture
def setup(tmp_path):
    """Set up a temporary KB with KBService for testing promotion."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    kb = KBConfig(name="test", path=kb_path, kb_type="journalism-investigation")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    kb_service = KBService(config, db)

    yield {"db": db, "kb_service": kb_service, "config": config}
    db.close()


def _create_claim(kb_service, claim_id, title, claim_status="corroborated", importance=7):
    """Helper to create a claim entry in the test KB."""
    kb_service.create_entry(
        kb_name="test",
        entry_id=claim_id,
        title=title,
        entry_type="claim",
        body="Test claim body.",
        assertion="Entity X owns Entity Y",
        claim_status=claim_status,
        confidence="high",
        importance=importance,
    )


class TestPromoteCorroboratedClaim:
    def test_promote_corroborated_claim(self, setup):
        """Creates claim with status corroborated, promotes it, verifies edge-entity created."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(kb_service, "claim-ownership-x-y", "X owns Y")

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-ownership-x-y",
            edge_type="ownership",
            kb_service=kb_service,
            endpoint_fields={"owner": "[[entity-x]]", "asset": "[[entity-y]]"},
        )

        assert "error" not in result
        assert "created" in result
        assert result["edge_type"] == "ownership"

        # Verify the edge entry actually exists in the DB
        edge_entry = db.get_entry(result["created"], "test")
        assert edge_entry is not None
        assert edge_entry["entry_type"] == "ownership"
        meta = edge_entry.get("metadata", {})
        assert meta.get("owner") == "[[entity-x]]"
        assert meta.get("asset") == "[[entity-y]]"

    def test_promote_partially_verified_claim(self, setup):
        """partially_verified claims should also be promotable."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(
            kb_service,
            "claim-funding-a-b",
            "A funds B",
            claim_status="partially_verified",
        )

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-funding-a-b",
            edge_type="funding",
            kb_service=kb_service,
            endpoint_fields={"funder": "[[entity-a]]", "recipient": "[[entity-b]]"},
        )

        assert "error" not in result
        assert result["edge_type"] == "funding"

    def test_promote_ownership_missing_endpoint_fields_is_an_error(self, setup):
        """Omitting owner/asset must be a clean error, not a raw SchemaViolationError."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(kb_service, "claim-ownership-missing", "X owns Y")

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-ownership-missing",
            edge_type="ownership",
            kb_service=kb_service,
        )

        assert "error" in result
        assert "owner" in result["error"] and "asset" in result["error"]
        # Nothing was created
        kb_path = setup["config"].knowledge_bases[0].path
        written = [p for p in kb_path.rglob("*.md") if p.parent.name != "claims"]
        assert not written, f"an edge was written: {written}"

    def test_promote_ownership_partial_endpoint_fields_is_an_error(self, setup):
        """Only one of owner/asset supplied must still be refused, naming the missing one."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(kb_service, "claim-ownership-partial", "X owns Y")

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-ownership-partial",
            edge_type="ownership",
            kb_service=kb_service,
            endpoint_fields={"owner": "[[entity-x]]"},
        )

        assert "error" in result
        assert "asset" in result["error"]

    def test_promote_ownership_whitespace_only_endpoint_field_is_an_error(self, setup):
        """A whitespace-only value (`"   "`) is truthy in Python, so a naive
        `not endpoint_fields.get(f)` check treats it as present -- it must
        count as missing, same as an empty string or an absent key."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(kb_service, "claim-ownership-whitespace", "X owns Y")

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-ownership-whitespace",
            edge_type="ownership",
            kb_service=kb_service,
            endpoint_fields={"owner": "[[entity-x]]", "asset": "   "},
        )

        assert "error" in result
        assert "asset" in result["error"]
        kb_path = setup["config"].knowledge_bases[0].path
        written = [p for p in kb_path.rglob("*.md") if p.parent.name != "claims"]
        assert not written, f"an edge was written: {written}"


class TestRejectUnverifiedClaim:
    def test_reject_unverified_claim(self, setup):
        """Claim with status 'unverified' should return error."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(
            kb_service,
            "claim-unverified",
            "Unverified claim",
            claim_status="unverified",
        )

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-unverified",
            edge_type="ownership",
            kb_service=kb_service,
        )

        assert "error" in result
        assert "unverified" in result["error"].lower() or "status" in result["error"].lower()

    def test_reject_disputed_claim(self, setup):
        """Claim with status 'disputed' should return error."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(
            kb_service,
            "claim-disputed",
            "Disputed claim",
            claim_status="disputed",
        )

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-disputed",
            edge_type="ownership",
            kb_service=kb_service,
        )

        assert "error" in result

    def test_reject_missing_claim(self, setup):
        """Nonexistent claim_id should return error."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="does-not-exist",
            edge_type="ownership",
            kb_service=kb_service,
        )

        assert "error" in result


class TestDryRunNoCreation:
    def test_dry_run_no_creation(self, setup):
        """dry_run returns proposed entry but doesn't create, when endpoint fields are valid."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(kb_service, "claim-dry-run", "Dry run claim")

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-dry-run",
            edge_type="ownership",
            kb_service=kb_service,
            endpoint_fields={"owner": "[[entity-x]]", "asset": "[[entity-y]]"},
            dry_run=True,
        )

        assert "error" not in result
        assert result.get("dry_run") is True
        assert "proposed" in result

        # Verify nothing was actually created
        proposed_id = result["proposed"]["entry_id"]
        edge_entry = db.get_entry(proposed_id, "test")
        assert edge_entry is None

    def test_dry_run_still_validates_missing_endpoint_fields(self, setup):
        """dry_run must run the same validation as a real promotion (coordinator note 1):
        a dry run that would fail for real must report the failure, not silent success."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(kb_service, "claim-dry-run-bad", "Dry run claim missing fields")

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-dry-run-bad",
            edge_type="ownership",
            kb_service=kb_service,
            dry_run=True,
        )

        assert "error" in result
        assert "owner" in result["error"] and "asset" in result["error"]
        assert result.get("dry_run") is not True or "proposed" not in result


class TestSourcedFromLink:
    def test_sourced_from_link(self, setup):
        """Promoted edge-entity has sourced_from link to original claim."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(kb_service, "claim-link-test", "Link test claim")

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-link-test",
            edge_type="membership",
            kb_service=kb_service,
            endpoint_fields={"person": "[[person-x]]", "organization": "[[org-y]]"},
        )

        assert "error" not in result
        created_id = result["created"]

        # Verify the edge entry has a sourced_from link to the claim
        edge_entry = db.get_entry(created_id, "test")
        assert edge_entry is not None

        links = edge_entry.get("links", [])
        sourced_from_links = [
            link
            for link in links
            if link.get("relation") == "sourced_from" and link.get("target_id") == "claim-link-test"
        ]
        assert len(sourced_from_links) == 1, (
            f"Expected sourced_from link to claim-link-test, got links: {links}"
        )


class TestEndpointFieldsAreChecked:
    """#422 delta cold read: endpoint_fields came straight from an MCP
    argument into create_entry. Only the edge type's own endpoint names are
    accepted, each a non-empty string; anything else is a clear refusal and
    writes nothing."""

    @pytest.mark.parametrize(
        "fields",
        [
            {"owner": "a", "asset": "b", "created_by": "x"},  # an extra key
            {"owner": "a", "asset": "b", "title": "x"},  # collides with a create_entry arg
            {"owner": {"x": 1}, "asset": ["y"]},  # not strings
            "owner=a",  # not a mapping
        ],
        ids=["extra-key", "colliding-key", "non-string", "not-a-mapping"],
    )
    def test_bad_endpoint_fields_are_refused(self, setup, fields):
        db = setup["db"]
        kb_service = setup["kb_service"]
        _create_claim(kb_service, "claim-bad-fields", "X owns Y")

        for dry_run in (True, False):
            result = promote_claim_to_edge(
                db=db,
                kb_name="test",
                claim_id="claim-bad-fields",
                edge_type="ownership",
                kb_service=kb_service,
                endpoint_fields=fields,
                dry_run=dry_run,
            )
            assert "error" in result, (dry_run, result)
            assert "keyword argument" not in result["error"], result
        kb_path = setup["config"].knowledge_bases[0].path
        written = [p for p in kb_path.rglob("*.md") if p.parent.name != "claims"]
        assert not written, f"an edge was written: {written}"
