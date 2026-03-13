"""Tests for beneficial ownership chain traversal."""

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB

from pyrite_journalism_investigation.ownership import (
    aggregate_ownership,
    trace_ownership_chain,
)

KB_NAME = "test-ownership"


@pytest.fixture
def db(tmp_path):
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    kb = KBConfig(name=KB_NAME, path=kb_path, kb_type="journalism-investigation")
    PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    db.register_kb(KB_NAME, "journalism-investigation", str(kb_path))
    yield db
    db.close()


def _upsert_ownership(db, entry_id, owner, asset, percentage, beneficial=False):
    """Helper to create an ownership entry."""
    meta = {
        "owner": f"[[{owner}]]",
        "asset": f"[[{asset}]]",
        "percentage": str(percentage),
    }
    if beneficial:
        meta["beneficial"] = True
    db.upsert_entry({
        "id": entry_id,
        "kb_name": KB_NAME,
        "title": f"{owner} owns {asset}",
        "entry_type": "ownership",
        "metadata": meta,
    })


def _upsert_entity(db, entry_id, title, entry_type="organization"):
    """Helper to create an entity entry."""
    db.upsert_entry({
        "id": entry_id,
        "kb_name": KB_NAME,
        "title": title,
        "entry_type": entry_type,
    })


def _upsert_membership(db, entry_id, member, organization):
    """Helper to create a membership entry."""
    db.upsert_entry({
        "id": entry_id,
        "kb_name": KB_NAME,
        "title": f"{member} member of {organization}",
        "entry_type": "membership",
        "metadata": {
            "member": f"[[{member}]]",
            "organization": f"[[{organization}]]",
        },
    })


class TestSimpleDirectOwnership:
    """Test case 1: A owns 100% of B."""

    def test_direct_ownership_single_owner(self, db):
        _upsert_entity(db, "person-a", "Person A", "person")
        _upsert_entity(db, "company-b", "Company B")
        _upsert_ownership(db, "own-a-b", "person-a", "company-b", 100)

        result = trace_ownership_chain(db, KB_NAME, "company-b")

        assert result["entity"]["id"] == "company-b"
        assert len(result["chains"]) == 1
        chain = result["chains"][0]
        assert chain["effective_percentage"] == 100.0
        assert len(chain["path"]) == 1
        assert chain["path"][0]["id"] == "person-a"

    def test_direct_ownership_beneficial_owners(self, db):
        _upsert_entity(db, "person-a", "Person A", "person")
        _upsert_entity(db, "company-b", "Company B")
        _upsert_ownership(db, "own-a-b", "person-a", "company-b", 100)

        result = trace_ownership_chain(db, KB_NAME, "company-b")

        assert len(result["beneficial_owners"]) == 1
        assert result["beneficial_owners"][0]["id"] == "person-a"


class TestTwoLevelChain:
    """Test case 2: A owns B owns C — percentage multiplication."""

    def test_two_level_effective_percentage(self, db):
        _upsert_entity(db, "person-a", "Person A", "person")
        _upsert_entity(db, "holding-b", "Holding B")
        _upsert_entity(db, "company-c", "Company C")
        _upsert_ownership(db, "own-a-b", "person-a", "holding-b", 80)
        _upsert_ownership(db, "own-b-c", "holding-b", "company-c", 50)

        result = trace_ownership_chain(db, KB_NAME, "company-c")

        assert len(result["chains"]) == 1
        chain = result["chains"][0]
        # 80% * 50% = 40%
        assert chain["effective_percentage"] == pytest.approx(40.0)
        assert len(chain["path"]) == 2
        assert chain["path"][0]["id"] == "holding-b"
        assert chain["path"][1]["id"] == "person-a"

    def test_two_level_beneficial_owner_is_top(self, db):
        _upsert_entity(db, "person-a", "Person A", "person")
        _upsert_entity(db, "holding-b", "Holding B")
        _upsert_entity(db, "company-c", "Company C")
        _upsert_ownership(db, "own-a-b", "person-a", "holding-b", 80)
        _upsert_ownership(db, "own-b-c", "holding-b", "company-c", 50)

        result = trace_ownership_chain(db, KB_NAME, "company-c")

        bo_ids = [bo["id"] for bo in result["beneficial_owners"]]
        assert "person-a" in bo_ids
        # holding-b is an intermediary, not a beneficial owner
        assert "holding-b" not in bo_ids


class TestMultipleOwners:
    """Test case 3: Multiple owners of same entity."""

    def test_multiple_direct_owners(self, db):
        _upsert_entity(db, "person-a", "Person A", "person")
        _upsert_entity(db, "person-b", "Person B", "person")
        _upsert_entity(db, "company-c", "Company C")
        _upsert_ownership(db, "own-a-c", "person-a", "company-c", 60)
        _upsert_ownership(db, "own-b-c", "person-b", "company-c", 40)

        result = trace_ownership_chain(db, KB_NAME, "company-c")

        assert len(result["chains"]) == 2
        bo_ids = {bo["id"] for bo in result["beneficial_owners"]}
        assert bo_ids == {"person-a", "person-b"}

    def test_multiple_owners_percentages(self, db):
        _upsert_entity(db, "person-a", "Person A", "person")
        _upsert_entity(db, "person-b", "Person B", "person")
        _upsert_entity(db, "company-c", "Company C")
        _upsert_ownership(db, "own-a-c", "person-a", "company-c", 60)
        _upsert_ownership(db, "own-b-c", "person-b", "company-c", 40)

        result = trace_ownership_chain(db, KB_NAME, "company-c")

        percentages = {
            chain["path"][-1]["id"]: chain["effective_percentage"]
            for chain in result["chains"]
        }
        assert percentages["person-a"] == pytest.approx(60.0)
        assert percentages["person-b"] == pytest.approx(40.0)


class TestShellCompanyDetection:
    """Test case 4: Shell company detection heuristic."""

    def test_shell_company_detected(self, db):
        """Entity that is intermediary (owner AND asset) with no memberships = shell."""
        _upsert_entity(db, "person-a", "Person A", "person")
        _upsert_entity(db, "shell-co", "Shell Co")
        _upsert_entity(db, "real-co", "Real Co")
        # person-a -> shell-co -> real-co
        _upsert_ownership(db, "own-a-shell", "person-a", "shell-co", 100)
        _upsert_ownership(db, "own-shell-real", "shell-co", "real-co", 100)

        result = trace_ownership_chain(db, KB_NAME, "real-co")

        shell_ids = [s["id"] for s in result["shell_indicators"]]
        assert "shell-co" in shell_ids

    def test_no_shell_if_has_memberships(self, db):
        """Entity with memberships is NOT flagged as shell."""
        _upsert_entity(db, "person-a", "Person A", "person")
        _upsert_entity(db, "legit-co", "Legit Co")
        _upsert_entity(db, "sub-co", "Sub Co")
        _upsert_ownership(db, "own-a-legit", "person-a", "legit-co", 100)
        _upsert_ownership(db, "own-legit-sub", "legit-co", "sub-co", 100)
        # legit-co has a member — not a shell
        _upsert_membership(db, "mem-emp-legit", "employee-1", "legit-co")

        result = trace_ownership_chain(db, KB_NAME, "sub-co")

        shell_ids = [s["id"] for s in result["shell_indicators"]]
        assert "legit-co" not in shell_ids


class TestCircularOwnership:
    """Test case 5: Circular ownership — must not infinite loop."""

    def test_circular_does_not_loop(self, db):
        _upsert_entity(db, "co-a", "Company A")
        _upsert_entity(db, "co-b", "Company B")
        # A owns B, B owns A — circular
        _upsert_ownership(db, "own-a-b", "co-a", "co-b", 50)
        _upsert_ownership(db, "own-b-a", "co-b", "co-a", 50)

        # Should terminate without hanging
        result = trace_ownership_chain(db, KB_NAME, "co-b")

        assert result is not None
        assert "chains" in result


class TestMaxDepthLimit:
    """Test case 6: Max depth limit."""

    def test_depth_limit_stops_traversal(self, db):
        # Create chain: e0 <- e1 <- e2 <- e3 <- e4 <- e5
        for i in range(6):
            _upsert_entity(db, f"ent-{i}", f"Entity {i}")
        for i in range(5):
            _upsert_ownership(db, f"own-{i}", f"ent-{i+1}", f"ent-{i}", 100)

        result = trace_ownership_chain(db, KB_NAME, "ent-0", max_depth=3)

        # Should not traverse beyond depth 3
        for chain in result["chains"]:
            assert len(chain["path"]) <= 3

    def test_default_depth_is_five(self, db):
        # Create chain of length 7: e0 <- e1 <- ... <- e7
        for i in range(8):
            _upsert_entity(db, f"ent-{i}", f"Entity {i}")
        for i in range(7):
            _upsert_ownership(db, f"own-{i}", f"ent-{i+1}", f"ent-{i}", 100)

        result = trace_ownership_chain(db, KB_NAME, "ent-0")

        for chain in result["chains"]:
            assert len(chain["path"]) <= 5


class TestNoOwnership:
    """Test case 7: Entity with no ownership found."""

    def test_no_owners(self, db):
        _upsert_entity(db, "standalone", "Standalone Corp")

        result = trace_ownership_chain(db, KB_NAME, "standalone")

        assert result["entity"]["id"] == "standalone"
        assert result["chains"] == []
        assert result["beneficial_owners"] == []
        assert result["shell_indicators"] == []


class TestAggregateOwnership:
    """Test case 8: Aggregate beneficial owners from multiple chains."""

    def test_aggregate_simple(self, db):
        _upsert_entity(db, "person-a", "Person A", "person")
        _upsert_entity(db, "company-b", "Company B")
        _upsert_ownership(db, "own-a-b", "person-a", "company-b", 75)

        result = aggregate_ownership(db, KB_NAME, "company-b")

        assert result["entity"]["id"] == "company-b"
        assert len(result["beneficial_owners"]) == 1
        bo = result["beneficial_owners"][0]
        assert bo["id"] == "person-a"
        assert bo["effective_percentage"] == pytest.approx(75.0)
        assert bo["via_chains"] == 1
        assert result["total_identified_ownership"] == pytest.approx(75.0)

    def test_aggregate_multiple_chains_same_owner(self, db):
        """Owner reaches target via two different intermediaries."""
        _upsert_entity(db, "person-a", "Person A", "person")
        _upsert_entity(db, "holding-x", "Holding X")
        _upsert_entity(db, "holding-y", "Holding Y")
        _upsert_entity(db, "target-co", "Target Co")
        # person-a -> holding-x (100%) -> target-co (30%)
        _upsert_ownership(db, "own-a-x", "person-a", "holding-x", 100)
        _upsert_ownership(db, "own-x-t", "holding-x", "target-co", 30)
        # person-a -> holding-y (50%) -> target-co (20%)
        _upsert_ownership(db, "own-a-y", "person-a", "holding-y", 50)
        _upsert_ownership(db, "own-y-t", "holding-y", "target-co", 20)

        result = aggregate_ownership(db, KB_NAME, "target-co")

        assert len(result["beneficial_owners"]) == 1
        bo = result["beneficial_owners"][0]
        assert bo["id"] == "person-a"
        # 100%*30% + 50%*20% = 30% + 10% = 40%
        assert bo["effective_percentage"] == pytest.approx(40.0)
        assert bo["via_chains"] == 2
        assert result["total_identified_ownership"] == pytest.approx(40.0)

    def test_aggregate_multiple_distinct_owners(self, db):
        _upsert_entity(db, "person-a", "Person A", "person")
        _upsert_entity(db, "person-b", "Person B", "person")
        _upsert_entity(db, "target-co", "Target Co")
        _upsert_ownership(db, "own-a-t", "person-a", "target-co", 51)
        _upsert_ownership(db, "own-b-t", "person-b", "target-co", 30)

        result = aggregate_ownership(db, KB_NAME, "target-co")

        assert len(result["beneficial_owners"]) == 2
        assert result["total_identified_ownership"] == pytest.approx(81.0)
