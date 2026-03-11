"""Tests for source reliability tier system."""

from pyrite_journalism_investigation.reliability import (
    SOURCE_TIERS,
    reliability_to_tier,
    tier_label,
    source_tier_distribution,
)
from pyrite_journalism_investigation.entry_types import ClaimEntry


class TestSourceTiers:
    def test_tier_mapping(self):
        assert reliability_to_tier("high") == 1
        assert reliability_to_tier("medium") == 2
        assert reliability_to_tier("low") == 3
        assert reliability_to_tier("unknown") == 3

    def test_tier_labels(self):
        assert tier_label(1) == "high"
        assert tier_label(2) == "medium"
        assert tier_label(3) == "low"

    def test_source_tiers_dict(self):
        assert SOURCE_TIERS["high"] == 1
        assert SOURCE_TIERS["medium"] == 2
        assert SOURCE_TIERS["low"] == 3
        assert SOURCE_TIERS["unknown"] == 3

    def test_tier_distribution(self):
        reliabilities = ["high", "high", "medium", "low", "unknown"]
        dist = source_tier_distribution(reliabilities)
        assert dist == {1: 2, 2: 1, 3: 2}

    def test_tier_distribution_empty(self):
        dist = source_tier_distribution([])
        assert dist == {}


class TestClaimConfidenceWithTiers:
    """Test that auto_confidence uses source tiers when provided."""

    def test_two_same_tier_sources_medium(self):
        entry = ClaimEntry(
            id="c1", title="Test",
            evidence_refs=["[[doc-1]]", "[[doc-2]]"],
        )
        # Without tier info, 2+ sources = medium
        assert entry.auto_confidence() == "medium"

    def test_two_different_tier_sources_high(self):
        entry = ClaimEntry(
            id="c1", title="Test",
            evidence_refs=["[[doc-1]]", "[[doc-2]]"],
        )
        # With tier info showing cross-corroboration
        tiers = {"[[doc-1]]": 1, "[[doc-2]]": 2}
        assert entry.auto_confidence(source_tiers=tiers) == "high"

    def test_two_same_tier_sources_with_tiers_medium(self):
        entry = ClaimEntry(
            id="c1", title="Test",
            evidence_refs=["[[doc-1]]", "[[doc-2]]"],
        )
        tiers = {"[[doc-1]]": 1, "[[doc-2]]": 1}
        assert entry.auto_confidence(source_tiers=tiers) == "medium"

    def test_disputed_overrides_tiers(self):
        entry = ClaimEntry(
            id="c1", title="Test",
            evidence_refs=["[[doc-1]]", "[[doc-2]]"],
            disputed_by=["[[counter-1]]"],
        )
        tiers = {"[[doc-1]]": 1, "[[doc-2]]": 2}
        assert entry.auto_confidence(source_tiers=tiers) == "low"

    def test_missing_tier_info_defaults_to_same_tier(self):
        """Sources not in tiers dict are treated as same tier."""
        entry = ClaimEntry(
            id="c1", title="Test",
            evidence_refs=["[[doc-1]]", "[[doc-2]]"],
        )
        # Empty tiers dict — all sources same default tier
        tiers: dict[str, int] = {}
        assert entry.auto_confidence(source_tiers=tiers) == "medium"
