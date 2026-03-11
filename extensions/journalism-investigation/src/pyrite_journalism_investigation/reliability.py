"""Source reliability tier system for investigative journalism."""

from collections import Counter

# Tier mapping: reliability level -> tier number (1 = most reliable)
SOURCE_TIERS: dict[str, int] = {
    "high": 1,
    "medium": 2,
    "low": 3,
    "unknown": 3,
}

_TIER_LABELS: dict[int, str] = {1: "high", 2: "medium", 3: "low"}


def reliability_to_tier(reliability: str) -> int:
    """Map a reliability level string to its numeric tier."""
    return SOURCE_TIERS.get(reliability, 3)


def tier_label(tier: int) -> str:
    """Get the label for a tier number."""
    return _TIER_LABELS.get(tier, "low")


def source_tier_distribution(reliabilities: list[str]) -> dict[int, int]:
    """Count sources per tier from a list of reliability levels."""
    if not reliabilities:
        return {}
    return dict(Counter(reliability_to_tier(r) for r in reliabilities))
