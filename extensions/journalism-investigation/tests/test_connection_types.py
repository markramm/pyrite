"""Tests for connection entry types (edge-entities)."""

from pyrite_journalism_investigation.entry_types import (
    FundingEntry,
    MembershipEntry,
    OwnershipEntry,
    FUNDING_MECHANISMS,
)


class TestOwnershipEntry:
    def test_entry_type(self):
        entry = OwnershipEntry(id="o1", title="X owns Y Corp")
        assert entry.entry_type == "ownership"

    def test_round_trip(self):
        entry = OwnershipEntry(
            id="o1",
            title="Doe owns Shell Corp",
            body="Beneficial ownership via nominee structure",
            owner="[[john-doe]]",
            asset="[[shell-corp-ltd]]",
            percentage="51%",
            start_date="2018-01-15",
            end_date="",
            legal_basis="Panama corporate registry",
            beneficial=True,
            importance=8,
        )
        meta = entry.to_frontmatter()
        assert meta["type"] == "ownership"
        assert meta["owner"] == "[[john-doe]]"
        assert meta["asset"] == "[[shell-corp-ltd]]"
        assert meta["percentage"] == "51%"
        assert meta["beneficial"] is True

        restored = OwnershipEntry.from_frontmatter(meta, "Beneficial ownership via nominee structure")
        assert restored.owner == "[[john-doe]]"
        assert restored.asset == "[[shell-corp-ltd]]"
        assert restored.percentage == "51%"
        assert restored.beneficial is True

    def test_defaults(self):
        entry = OwnershipEntry(id="o1", title="Test")
        assert entry.owner == ""
        assert entry.asset == ""
        assert entry.percentage == ""
        assert entry.start_date == ""
        assert entry.end_date == ""
        assert entry.legal_basis == ""
        assert entry.beneficial is False

    def test_to_frontmatter_omits_empty(self):
        entry = OwnershipEntry(id="o1", title="Test")
        meta = entry.to_frontmatter()
        assert "owner" not in meta
        assert "asset" not in meta
        assert "percentage" not in meta
        assert "beneficial" not in meta


class TestMembershipEntry:
    def test_entry_type(self):
        entry = MembershipEntry(id="m1", title="Doe on Board of X")
        assert entry.entry_type == "membership"

    def test_round_trip(self):
        entry = MembershipEntry(
            id="m1",
            title="Doe on Board of Acme",
            body="Appointed by shareholders in 2019",
            person="[[john-doe]]",
            organization="[[acme-corp]]",
            role="Board Director",
            start_date="2019-03-01",
            end_date="2022-12-31",
            importance=7,
        )
        meta = entry.to_frontmatter()
        assert meta["type"] == "membership"
        assert meta["person"] == "[[john-doe]]"
        assert meta["organization"] == "[[acme-corp]]"
        assert meta["role"] == "Board Director"

        restored = MembershipEntry.from_frontmatter(meta, "Appointed by shareholders in 2019")
        assert restored.person == "[[john-doe]]"
        assert restored.organization == "[[acme-corp]]"
        assert restored.role == "Board Director"

    def test_defaults(self):
        entry = MembershipEntry(id="m1", title="Test")
        assert entry.person == ""
        assert entry.organization == ""
        assert entry.role == ""
        assert entry.start_date == ""
        assert entry.end_date == ""

    def test_to_frontmatter_omits_empty(self):
        entry = MembershipEntry(id="m1", title="Test")
        meta = entry.to_frontmatter()
        assert "person" not in meta
        assert "organization" not in meta
        assert "role" not in meta


class TestFundingEntry:
    def test_entry_type(self):
        entry = FundingEntry(id="f1", title="X funds Y")
        assert entry.entry_type == "funding"

    def test_round_trip(self):
        entry = FundingEntry(
            id="f1",
            title="Corp A funds PAC B",
            body="Dark money channel via 501c4",
            funder="[[corp-a]]",
            recipient="[[pac-b]]",
            amount="2000000",
            currency="USD",
            date_range="2019-2022",
            purpose="Political influence",
            mechanism="dark_money",
            importance=9,
        )
        meta = entry.to_frontmatter()
        assert meta["type"] == "funding"
        assert meta["funder"] == "[[corp-a]]"
        assert meta["recipient"] == "[[pac-b]]"
        assert meta["amount"] == "2000000"
        assert meta["mechanism"] == "dark_money"

        restored = FundingEntry.from_frontmatter(meta, "Dark money channel via 501c4")
        assert restored.funder == "[[corp-a]]"
        assert restored.recipient == "[[pac-b]]"
        assert restored.amount == "2000000"
        assert restored.mechanism == "dark_money"

    def test_defaults(self):
        entry = FundingEntry(id="f1", title="Test")
        assert entry.funder == ""
        assert entry.recipient == ""
        assert entry.amount == ""
        assert entry.currency == ""
        assert entry.date_range == ""
        assert entry.purpose == ""
        assert entry.mechanism == ""

    def test_to_frontmatter_omits_empty(self):
        entry = FundingEntry(id="f1", title="Test")
        meta = entry.to_frontmatter()
        assert "funder" not in meta
        assert "recipient" not in meta
        assert "amount" not in meta
        assert "mechanism" not in meta

    def test_funding_mechanism_values(self):
        assert "grant" in FUNDING_MECHANISMS
        assert "donation" in FUNDING_MECHANISMS
        assert "contract" in FUNDING_MECHANISMS
        assert "lobbying" in FUNDING_MECHANISMS
        assert "dark_money" in FUNDING_MECHANISMS
        assert "other" in FUNDING_MECHANISMS
