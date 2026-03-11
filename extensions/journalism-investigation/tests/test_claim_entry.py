"""Tests for ClaimEntry type and lifecycle."""

from pyrite_journalism_investigation.entry_types import ClaimEntry, CLAIM_STATUSES, CONFIDENCE_LEVELS


class TestClaimEntry:
    def test_entry_type(self):
        entry = ClaimEntry(id="c1", title="Test claim", assertion="X paid Y")
        assert entry.entry_type == "claim"

    def test_round_trip(self):
        entry = ClaimEntry(
            id="c1",
            title="Bribe allegation",
            body="Detailed narrative",
            assertion="Entity X paid $500k to Entity Y",
            confidence="medium",
            claim_status="partially_verified",
            evidence_refs=["[[doc-leak-1]]", "[[doc-filing-2]]"],
            disputed_by=["[[claim-counter-1]]"],
            importance=8,
        )
        meta = entry.to_frontmatter()
        assert meta["type"] == "claim"
        assert meta["assertion"] == "Entity X paid $500k to Entity Y"
        assert meta["confidence"] == "medium"
        assert meta["claim_status"] == "partially_verified"
        assert meta["evidence_refs"] == ["[[doc-leak-1]]", "[[doc-filing-2]]"]
        assert meta["disputed_by"] == ["[[claim-counter-1]]"]

        restored = ClaimEntry.from_frontmatter(meta, "Detailed narrative")
        assert restored.id == "c1"
        assert restored.assertion == "Entity X paid $500k to Entity Y"
        assert restored.confidence == "medium"
        assert restored.claim_status == "partially_verified"
        assert restored.evidence_refs == ["[[doc-leak-1]]", "[[doc-filing-2]]"]
        assert restored.disputed_by == ["[[claim-counter-1]]"]
        assert restored.importance == 8

    def test_defaults(self):
        entry = ClaimEntry(id="c1", title="Test")
        assert entry.assertion == ""
        assert entry.confidence == "low"
        assert entry.claim_status == "unverified"
        assert entry.evidence_refs == []
        assert entry.disputed_by == []
        assert entry.importance == 5

    def test_to_frontmatter_omits_empty(self):
        entry = ClaimEntry(id="c1", title="Test")
        meta = entry.to_frontmatter()
        assert "evidence_refs" not in meta
        assert "disputed_by" not in meta
        # Defaults should still be omitted
        assert "confidence" not in meta or meta["confidence"] == "low"
        assert "claim_status" not in meta or meta["claim_status"] == "unverified"

    def test_claim_status_values(self):
        assert "unverified" in CLAIM_STATUSES
        assert "partially_verified" in CLAIM_STATUSES
        assert "corroborated" in CLAIM_STATUSES
        assert "disputed" in CLAIM_STATUSES
        assert "retracted" in CLAIM_STATUSES

    def test_confidence_values(self):
        assert "high" in CONFIDENCE_LEVELS
        assert "medium" in CONFIDENCE_LEVELS
        assert "low" in CONFIDENCE_LEVELS


class TestClaimStatusTransitions:
    """Test that status transitions follow the allowed lifecycle."""

    def test_valid_transitions_from_unverified(self):
        assert ClaimEntry.valid_transitions("unverified") == {"partially_verified"}

    def test_valid_transitions_from_partially_verified(self):
        assert ClaimEntry.valid_transitions("partially_verified") == {"corroborated", "disputed"}

    def test_valid_transitions_from_disputed(self):
        assert ClaimEntry.valid_transitions("disputed") == {"retracted", "corroborated"}

    def test_valid_transitions_from_corroborated(self):
        # Terminal state, no transitions
        assert ClaimEntry.valid_transitions("corroborated") == set()

    def test_valid_transitions_from_retracted(self):
        # Terminal state, no transitions
        assert ClaimEntry.valid_transitions("retracted") == set()

    def test_can_transition_valid(self):
        entry = ClaimEntry(id="c1", title="Test", claim_status="unverified")
        assert entry.can_transition_to("partially_verified") is True

    def test_can_transition_invalid(self):
        entry = ClaimEntry(id="c1", title="Test", claim_status="unverified")
        assert entry.can_transition_to("corroborated") is False

    def test_can_transition_from_disputed_to_corroborated(self):
        entry = ClaimEntry(id="c1", title="Test", claim_status="disputed")
        assert entry.can_transition_to("corroborated") is True


class TestClaimConfidenceCalculation:
    """Test auto-calculation of confidence from evidence."""

    def test_no_sources_low(self):
        entry = ClaimEntry(id="c1", title="Test", evidence_refs=[])
        assert entry.auto_confidence() == "low"

    def test_one_source_low(self):
        entry = ClaimEntry(id="c1", title="Test", evidence_refs=["[[doc-1]]"])
        assert entry.auto_confidence() == "low"

    def test_two_sources_medium(self):
        entry = ClaimEntry(
            id="c1", title="Test",
            evidence_refs=["[[doc-1]]", "[[doc-2]]"],
        )
        assert entry.auto_confidence() == "medium"

    def test_disputed_always_low(self):
        entry = ClaimEntry(
            id="c1", title="Test",
            evidence_refs=["[[doc-1]]", "[[doc-2]]", "[[doc-3]]"],
            disputed_by=["[[counter-1]]"],
        )
        assert entry.auto_confidence() == "low"
