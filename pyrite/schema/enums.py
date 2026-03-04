"""Enumeration types for KB schema."""

from enum import StrEnum


class VerificationStatus(StrEnum):
    """Verification status for sources and claims."""

    UNVERIFIED = "unverified"
    CLAIMED = "claimed"
    REVIEWED = "reviewed"
    VERIFIED = "verified"
    DISPUTED = "disputed"


class EventStatus(StrEnum):
    """Status for timeline events."""

    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    ALLEGED = "alleged"
    RUMORED = "rumored"


class ResearchStatus(StrEnum):
    """Research completion status."""

    STUB = "stub"
    PARTIAL = "partial"
    DRAFT = "draft"
    COMPLETE = "complete"
    PUBLISHED = "published"
