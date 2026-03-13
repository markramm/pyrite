"""Tests for claim-to-edge promotion feature."""

import pytest
from dataclasses import dataclass

from pyrite.config import PyriteConfig, Settings, KBConfig
from pyrite.storage.database import PyriteDB
from pyrite.services.kb_service import KBService

from pyrite_journalism_investigation.promote import promote_claim_to_edge


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
        )

        assert "error" not in result
        assert "created" in result
        assert result["edge_type"] == "ownership"

        # Verify the edge entry actually exists in the DB
        edge_entry = db.get_entry(result["created"], "test")
        assert edge_entry is not None
        assert edge_entry["entry_type"] == "ownership"

    def test_promote_partially_verified_claim(self, setup):
        """partially_verified claims should also be promotable."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(
            kb_service, "claim-funding-a-b", "A funds B",
            claim_status="partially_verified",
        )

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-funding-a-b",
            edge_type="funding",
            kb_service=kb_service,
        )

        assert "error" not in result
        assert result["edge_type"] == "funding"


class TestRejectUnverifiedClaim:
    def test_reject_unverified_claim(self, setup):
        """Claim with status 'unverified' should return error."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(
            kb_service, "claim-unverified", "Unverified claim",
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
            kb_service, "claim-disputed", "Disputed claim",
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
        """dry_run returns proposed entry but doesn't create."""
        db = setup["db"]
        kb_service = setup["kb_service"]

        _create_claim(kb_service, "claim-dry-run", "Dry run claim")

        result = promote_claim_to_edge(
            db=db,
            kb_name="test",
            claim_id="claim-dry-run",
            edge_type="ownership",
            kb_service=kb_service,
            dry_run=True,
        )

        assert "error" not in result
        assert result.get("dry_run") is True
        assert "proposed" in result

        # Verify nothing was actually created
        proposed_id = result["proposed"]["entry_id"]
        edge_entry = db.get_entry(proposed_id, "test")
        assert edge_entry is None


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
        )

        assert "error" not in result
        created_id = result["created"]

        # Verify the edge entry has a sourced_from link to the claim
        edge_entry = db.get_entry(created_id, "test")
        assert edge_entry is not None

        links = edge_entry.get("links", [])
        sourced_from_links = [
            link for link in links
            if link.get("relation") == "sourced_from"
            and link.get("target_id") == "claim-link-test"
        ]
        assert len(sourced_from_links) == 1, (
            f"Expected sourced_from link to claim-link-test, got links: {links}"
        )
