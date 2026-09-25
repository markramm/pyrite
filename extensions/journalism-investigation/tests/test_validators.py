"""Tests for journalism-investigation validators.

The validator binds the plugin contract (#379, #376, #48):
``(entry_type: str, fields: dict, ctx: dict) -> list[dict]``. These tests
call it directly with plain dicts rather than building Entry objects, since
that's what the registry actually passes at call time.
"""

from pyrite_journalism_investigation.plugin import _validate_investigation_entry

CTX: dict = {}


def _messages(errors: list[dict]) -> list[str]:
    return [e.get("message", "") for e in errors]


class TestAssetValidation:
    def test_valid_asset(self):
        errors = _validate_investigation_entry("asset", {"asset_type": "real_estate"}, CTX)
        assert errors == []

    def test_missing_asset_type(self):
        errors = _validate_investigation_entry("asset", {}, CTX)
        assert any("asset_type" in m for m in _messages(errors))

    def test_invalid_asset_type(self):
        errors = _validate_investigation_entry("asset", {"asset_type": "spaceship"}, CTX)
        assert any("asset_type" in m for m in _messages(errors))


class TestAccountValidation:
    def test_valid_account(self):
        errors = _validate_investigation_entry("account", {"account_type": "bank"}, CTX)
        assert errors == []

    def test_missing_account_type(self):
        errors = _validate_investigation_entry("account", {}, CTX)
        assert any("account_type" in m for m in _messages(errors))

    def test_invalid_account_type(self):
        errors = _validate_investigation_entry("account", {"account_type": "spaceship"}, CTX)
        assert any("account_type" in m for m in _messages(errors))


class TestDocumentSourceValidation:
    def test_valid_document_source(self):
        errors = _validate_investigation_entry("document_source", {"reliability": "high"}, CTX)
        assert errors == []

    def test_default_reliability_is_valid(self):
        """Default 'unknown' is a valid reliability level."""
        errors = _validate_investigation_entry("document_source", {"reliability": "unknown"}, CTX)
        assert errors == []

    def test_invalid_reliability(self):
        errors = _validate_investigation_entry("document_source", {"reliability": "excellent"}, CTX)
        assert any("reliability" in m for m in _messages(errors))


class TestInvestigationEventValidation:
    def test_valid_event(self):
        errors = _validate_investigation_entry("investigation_event", {"date": "2020-01-01"}, CTX)
        assert errors == []

    def test_missing_date(self):
        errors = _validate_investigation_entry("investigation_event", {}, CTX)
        assert any("date" in m for m in _messages(errors))


class TestTransactionValidation:
    def test_valid_transaction(self):
        errors = _validate_investigation_entry(
            "transaction",
            {"date": "2020-01-01", "sender": "A", "receiver": "B"},
            CTX,
        )
        assert errors == []

    def test_missing_date(self):
        errors = _validate_investigation_entry("transaction", {"sender": "A", "receiver": "B"}, CTX)
        assert any("date" in m for m in _messages(errors))

    def test_missing_sender(self):
        errors = _validate_investigation_entry(
            "transaction", {"date": "2020-01-01", "receiver": "B"}, CTX
        )
        assert any("sender" in m for m in _messages(errors))

    def test_missing_receiver(self):
        errors = _validate_investigation_entry(
            "transaction", {"date": "2020-01-01", "sender": "A"}, CTX
        )
        assert any("receiver" in m for m in _messages(errors))

    def test_bribe_requires_amount(self):
        errors = _validate_investigation_entry(
            "transaction",
            {
                "date": "2020-01-01",
                "sender": "A",
                "receiver": "B",
                "transaction_type": "bribe",
            },
            CTX,
        )
        assert any("amount" in m for m in _messages(errors))

    def test_bribe_with_amount_valid(self):
        errors = _validate_investigation_entry(
            "transaction",
            {
                "date": "2020-01-01",
                "sender": "A",
                "receiver": "B",
                "transaction_type": "bribe",
                "amount": "500000",
            },
            CTX,
        )
        assert errors == []

    def test_donation_no_amount_ok(self):
        """Non-payment types don't require amount."""
        errors = _validate_investigation_entry(
            "transaction",
            {
                "date": "2020-01-01",
                "sender": "A",
                "receiver": "B",
                "transaction_type": "donation",
            },
            CTX,
        )
        assert errors == []

    def test_invalid_transaction_type(self):
        errors = _validate_investigation_entry(
            "transaction",
            {
                "date": "2020-01-01",
                "sender": "A",
                "receiver": "B",
                "transaction_type": "teleportation",
            },
            CTX,
        )
        assert any("transaction_type" in m for m in _messages(errors))


class TestLegalActionValidation:
    def test_valid_legal_action(self):
        errors = _validate_investigation_entry(
            "legal_action",
            {"date": "2020-01-01", "case_type": "criminal", "jurisdiction": "US"},
            CTX,
        )
        assert errors == []

    def test_missing_date(self):
        errors = _validate_investigation_entry(
            "legal_action",
            {"case_type": "criminal", "jurisdiction": "US"},
            CTX,
        )
        assert any("date" in m for m in _messages(errors))

    def test_missing_case_type(self):
        errors = _validate_investigation_entry(
            "legal_action",
            {"date": "2020-01-01", "jurisdiction": "US"},
            CTX,
        )
        assert any("case_type" in m for m in _messages(errors))

    def test_missing_jurisdiction(self):
        errors = _validate_investigation_entry(
            "legal_action",
            {"date": "2020-01-01", "case_type": "criminal"},
            CTX,
        )
        assert any("jurisdiction" in m for m in _messages(errors))

    def test_invalid_case_type(self):
        errors = _validate_investigation_entry(
            "legal_action",
            {"date": "2020-01-01", "case_type": "kangaroo_court", "jurisdiction": "US"},
            CTX,
        )
        assert any("case_type" in m for m in _messages(errors))

    def test_invalid_case_status(self):
        errors = _validate_investigation_entry(
            "legal_action",
            {
                "date": "2020-01-01",
                "case_type": "criminal",
                "jurisdiction": "US",
                "case_status": "vibes",
            },
            CTX,
        )
        assert any("case_status" in m for m in _messages(errors))


class TestOwnershipValidation:
    def test_valid_ownership(self):
        errors = _validate_investigation_entry(
            "ownership", {"owner": "[[x]]", "asset": "[[y]]"}, CTX
        )
        assert errors == []

    def test_missing_owner(self):
        errors = _validate_investigation_entry("ownership", {"asset": "[[y]]"}, CTX)
        assert any("owner" in m for m in _messages(errors))

    def test_missing_asset(self):
        errors = _validate_investigation_entry("ownership", {"owner": "[[x]]"}, CTX)
        assert any("asset" in m for m in _messages(errors))


class TestMembershipValidation:
    def test_valid_membership(self):
        errors = _validate_investigation_entry(
            "membership", {"person": "[[x]]", "organization": "[[y]]"}, CTX
        )
        assert errors == []

    def test_missing_person(self):
        errors = _validate_investigation_entry("membership", {"organization": "[[y]]"}, CTX)
        assert any("person" in m for m in _messages(errors))

    def test_missing_organization(self):
        errors = _validate_investigation_entry("membership", {"person": "[[x]]"}, CTX)
        assert any("organization" in m for m in _messages(errors))


class TestFundingValidation:
    def test_valid_funding(self):
        errors = _validate_investigation_entry(
            "funding", {"funder": "[[x]]", "recipient": "[[y]]"}, CTX
        )
        assert errors == []

    def test_missing_funder(self):
        errors = _validate_investigation_entry("funding", {"recipient": "[[y]]"}, CTX)
        assert any("funder" in m for m in _messages(errors))

    def test_missing_recipient(self):
        errors = _validate_investigation_entry("funding", {"funder": "[[x]]"}, CTX)
        assert any("recipient" in m for m in _messages(errors))

    def test_invalid_mechanism(self):
        errors = _validate_investigation_entry(
            "funding",
            {"funder": "[[x]]", "recipient": "[[y]]", "mechanism": "telepathy"},
            CTX,
        )
        assert any("mechanism" in m for m in _messages(errors))


class TestEvidenceValidation:
    def test_valid_evidence(self):
        errors = _validate_investigation_entry("evidence", {"evidence_type": "record"}, CTX)
        assert errors == []

    def test_missing_evidence_type(self):
        errors = _validate_investigation_entry("evidence", {}, CTX)
        assert any("evidence_type" in m for m in _messages(errors))

    def test_invalid_evidence_type(self):
        errors = _validate_investigation_entry("evidence", {"evidence_type": "telepathy"}, CTX)
        assert any("evidence_type" in m for m in _messages(errors))


class TestClaimValidation:
    def test_valid_claim(self):
        errors = _validate_investigation_entry("claim", {"assertion": "X paid Y"}, CTX)
        assert errors == []

    def test_missing_assertion(self):
        errors = _validate_investigation_entry("claim", {}, CTX)
        assert any("assertion" in m for m in _messages(errors))

    def test_invalid_claim_status(self):
        errors = _validate_investigation_entry(
            "claim",
            {"assertion": "X paid Y", "claim_status": "bogus"},
            CTX,
        )
        assert any("claim_status" in m.lower() or "status" in m.lower() for m in _messages(errors))

    def test_invalid_confidence(self):
        errors = _validate_investigation_entry(
            "claim",
            {"assertion": "X paid Y", "confidence": "very_high"},
            CTX,
        )
        assert any("confidence" in m.lower() for m in _messages(errors))


class TestImportanceValidation:
    def test_valid_importance(self):
        errors = _validate_investigation_entry(
            "asset", {"asset_type": "other", "importance": 5}, CTX
        )
        assert errors == []

    def test_importance_too_low(self):
        errors = _validate_investigation_entry(
            "asset", {"asset_type": "other", "importance": 0}, CTX
        )
        assert any("Importance" in m for m in _messages(errors))

    def test_importance_too_high(self):
        errors = _validate_investigation_entry(
            "asset", {"asset_type": "other", "importance": 11}, CTX
        )
        assert any("Importance" in m for m in _messages(errors))
