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

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    REPORTED = "reported"
    DEVELOPING = "developing"
    DISPUTED = "disputed"
    ALLEGED = "alleged"
    RUMORED = "rumored"
    PROVEN = "proven"


class ResearchStatus(StrEnum):
    """Research completion status."""

    STUB = "stub"
    PARTIAL = "partial"
    DRAFT = "draft"
    COMPLETE = "complete"
    PUBLISHED = "published"
