"""Tests for journalism-investigation validators."""

from pyrite_journalism_investigation.entry_types import (
    AccountEntry,
    AssetEntry,
    ClaimEntry,
    DocumentSourceEntry,
    EvidenceEntry,
    FundingEntry,
    InvestigationEventEntry,
    LegalActionEntry,
    MembershipEntry,
    OwnershipEntry,
    TransactionEntry,
)
from pyrite_journalism_investigation.plugin import _validate_investigation_entry


class TestAssetValidation:
    def test_valid_asset(self):
        entry = AssetEntry(id="test", title="Test", asset_type="real_estate")
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_missing_asset_type(self):
        entry = AssetEntry(id="test", title="Test")
        errors = _validate_investigation_entry(entry)
        assert any("asset_type" in e for e in errors)

    def test_invalid_asset_type(self):
        entry = AssetEntry(id="test", title="Test", asset_type="spaceship")
        errors = _validate_investigation_entry(entry)
        assert any("asset_type" in e for e in errors)


class TestAccountValidation:
    def test_valid_account(self):
        entry = AccountEntry(id="test", title="Test", account_type="bank")
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_missing_account_type(self):
        entry = AccountEntry(id="test", title="Test")
        errors = _validate_investigation_entry(entry)
        assert any("account_type" in e for e in errors)

    def test_invalid_account_type(self):
        entry = AccountEntry(id="test", title="Test", account_type="spaceship")
        errors = _validate_investigation_entry(entry)
        assert any("account_type" in e for e in errors)


class TestDocumentSourceValidation:
    def test_valid_document_source(self):
        entry = DocumentSourceEntry(id="test", title="Test", reliability="high")
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_default_reliability_is_valid(self):
        """Default 'unknown' is a valid reliability level."""
        entry = DocumentSourceEntry(id="test", title="Test")
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_invalid_reliability(self):
        entry = DocumentSourceEntry(id="test", title="Test", reliability="excellent")
        errors = _validate_investigation_entry(entry)
        assert any("reliability" in e for e in errors)


class TestInvestigationEventValidation:
    def test_valid_event(self):
        entry = InvestigationEventEntry(id="test", title="Test", date="2020-01-01")
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_missing_date(self):
        entry = InvestigationEventEntry(id="test", title="Test")
        errors = _validate_investigation_entry(entry)
        assert any("date" in e for e in errors)


class TestTransactionValidation:
    def test_valid_transaction(self):
        entry = TransactionEntry(
            id="test", title="Test", date="2020-01-01",
            sender="A", receiver="B",
        )
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_missing_date(self):
        entry = TransactionEntry(id="test", title="Test", sender="A", receiver="B")
        errors = _validate_investigation_entry(entry)
        assert any("date" in e for e in errors)

    def test_missing_sender(self):
        entry = TransactionEntry(
            id="test", title="Test", date="2020-01-01", receiver="B",
        )
        errors = _validate_investigation_entry(entry)
        assert any("sender" in e for e in errors)

    def test_missing_receiver(self):
        entry = TransactionEntry(
            id="test", title="Test", date="2020-01-01", sender="A",
        )
        errors = _validate_investigation_entry(entry)
        assert any("receiver" in e for e in errors)

    def test_bribe_requires_amount(self):
        entry = TransactionEntry(
            id="test", title="Test", date="2020-01-01",
            sender="A", receiver="B", transaction_type="bribe",
        )
        errors = _validate_investigation_entry(entry)
        assert any("amount" in e for e in errors)

    def test_bribe_with_amount_valid(self):
        entry = TransactionEntry(
            id="test", title="Test", date="2020-01-01",
            sender="A", receiver="B", transaction_type="bribe", amount="500000",
        )
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_donation_no_amount_ok(self):
        """Non-payment types don't require amount."""
        entry = TransactionEntry(
            id="test", title="Test", date="2020-01-01",
            sender="A", receiver="B", transaction_type="donation",
        )
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_invalid_transaction_type(self):
        entry = TransactionEntry(
            id="test", title="Test", date="2020-01-01",
            sender="A", receiver="B", transaction_type="teleportation",
        )
        errors = _validate_investigation_entry(entry)
        assert any("transaction_type" in e for e in errors)


class TestLegalActionValidation:
    def test_valid_legal_action(self):
        entry = LegalActionEntry(
            id="test", title="Test", date="2020-01-01",
            case_type="criminal", jurisdiction="US",
        )
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_missing_date(self):
        entry = LegalActionEntry(
            id="test", title="Test", case_type="criminal", jurisdiction="US",
        )
        errors = _validate_investigation_entry(entry)
        assert any("date" in e for e in errors)

    def test_missing_case_type(self):
        entry = LegalActionEntry(
            id="test", title="Test", date="2020-01-01", jurisdiction="US",
        )
        errors = _validate_investigation_entry(entry)
        assert any("case_type" in e for e in errors)

    def test_missing_jurisdiction(self):
        entry = LegalActionEntry(
            id="test", title="Test", date="2020-01-01", case_type="criminal",
        )
        errors = _validate_investigation_entry(entry)
        assert any("jurisdiction" in e for e in errors)

    def test_invalid_case_type(self):
        entry = LegalActionEntry(
            id="test", title="Test", date="2020-01-01",
            case_type="kangaroo_court", jurisdiction="US",
        )
        errors = _validate_investigation_entry(entry)
        assert any("case_type" in e for e in errors)

    def test_invalid_case_status(self):
        entry = LegalActionEntry(
            id="test", title="Test", date="2020-01-01",
            case_type="criminal", jurisdiction="US", case_status="vibes",
        )
        errors = _validate_investigation_entry(entry)
        assert any("case_status" in e for e in errors)


class TestOwnershipValidation:
    def test_valid_ownership(self):
        entry = OwnershipEntry(id="test", title="Test", owner="[[x]]", asset="[[y]]")
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_missing_owner(self):
        entry = OwnershipEntry(id="test", title="Test", asset="[[y]]")
        errors = _validate_investigation_entry(entry)
        assert any("owner" in e for e in errors)

    def test_missing_asset(self):
        entry = OwnershipEntry(id="test", title="Test", owner="[[x]]")
        errors = _validate_investigation_entry(entry)
        assert any("asset" in e for e in errors)


class TestMembershipValidation:
    def test_valid_membership(self):
        entry = MembershipEntry(id="test", title="Test", person="[[x]]", organization="[[y]]")
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_missing_person(self):
        entry = MembershipEntry(id="test", title="Test", organization="[[y]]")
        errors = _validate_investigation_entry(entry)
        assert any("person" in e for e in errors)

    def test_missing_organization(self):
        entry = MembershipEntry(id="test", title="Test", person="[[x]]")
        errors = _validate_investigation_entry(entry)
        assert any("organization" in e for e in errors)


class TestFundingValidation:
    def test_valid_funding(self):
        entry = FundingEntry(id="test", title="Test", funder="[[x]]", recipient="[[y]]")
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_missing_funder(self):
        entry = FundingEntry(id="test", title="Test", recipient="[[y]]")
        errors = _validate_investigation_entry(entry)
        assert any("funder" in e for e in errors)

    def test_missing_recipient(self):
        entry = FundingEntry(id="test", title="Test", funder="[[x]]")
        errors = _validate_investigation_entry(entry)
        assert any("recipient" in e for e in errors)

    def test_invalid_mechanism(self):
        entry = FundingEntry(
            id="test", title="Test", funder="[[x]]", recipient="[[y]]",
            mechanism="telepathy",
        )
        errors = _validate_investigation_entry(entry)
        assert any("mechanism" in e for e in errors)


class TestEvidenceValidation:
    def test_valid_evidence(self):
        entry = EvidenceEntry(id="test", title="Test", evidence_type="record")
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_missing_evidence_type(self):
        entry = EvidenceEntry(id="test", title="Test")
        errors = _validate_investigation_entry(entry)
        assert any("evidence_type" in e for e in errors)

    def test_invalid_evidence_type(self):
        entry = EvidenceEntry(id="test", title="Test", evidence_type="telepathy")
        errors = _validate_investigation_entry(entry)
        assert any("evidence_type" in e for e in errors)


class TestClaimValidation:
    def test_valid_claim(self):
        entry = ClaimEntry(
            id="test", title="Test", assertion="X paid Y",
        )
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_missing_assertion(self):
        entry = ClaimEntry(id="test", title="Test")
        errors = _validate_investigation_entry(entry)
        assert any("assertion" in e for e in errors)

    def test_invalid_claim_status(self):
        entry = ClaimEntry(
            id="test", title="Test", assertion="X paid Y",
            claim_status="bogus",
        )
        errors = _validate_investigation_entry(entry)
        assert any("claim_status" in e.lower() or "status" in e.lower() for e in errors)

    def test_invalid_confidence(self):
        entry = ClaimEntry(
            id="test", title="Test", assertion="X paid Y",
            confidence="very_high",
        )
        errors = _validate_investigation_entry(entry)
        assert any("confidence" in e.lower() for e in errors)


class TestImportanceValidation:
    def test_valid_importance(self):
        entry = AssetEntry(id="test", title="Test", asset_type="other", importance=5)
        errors = _validate_investigation_entry(entry)
        assert errors == []

    def test_importance_too_low(self):
        entry = AssetEntry(id="test", title="Test", asset_type="other", importance=0)
        errors = _validate_investigation_entry(entry)
        assert any("Importance" in e for e in errors)

    def test_importance_too_high(self):
        entry = AssetEntry(id="test", title="Test", asset_type="other", importance=11)
        errors = _validate_investigation_entry(entry)
        assert any("Importance" in e for e in errors)
