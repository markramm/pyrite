"""Round-trip tests for journalism-investigation entity entry types."""

from pyrite_journalism_investigation.entry_types import (
    AccountEntry,
    AssetEntry,
    DocumentSourceEntry,
)


class TestAssetEntry:
    def test_entry_type(self):
        e = AssetEntry(id="mansion-london-belgravia", title="London Belgravia Mansion")
        assert e.entry_type == "asset"

    def test_round_trip(self):
        meta = {
            "id": "mansion-london-belgravia",
            "title": "London Belgravia Mansion",
            "type": "asset",
            "asset_type": "real_estate",
            "value": "50000000",
            "currency": "GBP",
            "jurisdiction": "United Kingdom",
            "registered_owner": "[[cyprus-nominee-corp]]",
            "acquisition_date": "2008-03-15",
            "description": "Grade II listed townhouse",
            "importance": 8,
            "tags": ["london", "luxury", "nominee-structure"],
        }
        body = "Five-storey Belgravia townhouse acquired through Cyprus nominee."
        entry = AssetEntry.from_frontmatter(meta, body)

        assert entry.id == "mansion-london-belgravia"
        assert entry.asset_type == "real_estate"
        assert entry.value == "50000000"
        assert entry.currency == "GBP"
        assert entry.jurisdiction == "United Kingdom"
        assert entry.registered_owner == "[[cyprus-nominee-corp]]"
        assert entry.acquisition_date == "2008-03-15"
        assert entry.description == "Grade II listed townhouse"
        assert entry.importance == 8
        assert entry.body == body

        fm = entry.to_frontmatter()
        assert fm["type"] == "asset"
        assert fm["asset_type"] == "real_estate"
        assert fm["value"] == "50000000"
        assert fm["currency"] == "GBP"
        assert fm["jurisdiction"] == "United Kingdom"

    def test_null_fields_produce_empty_strings(self):
        """YAML null values should become empty strings, not 'None'."""
        meta = {"title": "Test", "value": None, "acquisition_date": None}
        entry = AssetEntry.from_frontmatter(meta, "")
        assert entry.value == ""
        assert entry.acquisition_date == ""

    def test_defaults(self):
        entry = AssetEntry.from_frontmatter({"title": "Unknown Asset"}, "")
        assert entry.asset_type == ""
        assert entry.value == ""
        assert entry.currency == ""
        assert entry.jurisdiction == ""
        assert entry.registered_owner == ""
        assert entry.acquisition_date == ""
        assert entry.description == ""

    def test_asset_type_values(self):
        """All asset types from the spec should be valid."""
        valid_types = [
            "real_estate", "vehicle", "vessel", "aircraft",
            "luxury_good", "intellectual_property", "other",
        ]
        for asset_type in valid_types:
            entry = AssetEntry.from_frontmatter(
                {"title": "Test", "asset_type": asset_type}, ""
            )
            assert entry.asset_type == asset_type

    def test_to_frontmatter_omits_empty(self):
        """Empty optional fields should not appear in frontmatter."""
        entry = AssetEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "value" not in fm
        assert "currency" not in fm
        assert "jurisdiction" not in fm
        assert "registered_owner" not in fm
        assert "acquisition_date" not in fm
        assert "description" not in fm


class TestAccountEntry:
    def test_entry_type(self):
        e = AccountEntry(id="account-ubs-zurich-001", title="UBS Zurich Account")
        assert e.entry_type == "account"

    def test_round_trip(self):
        meta = {
            "id": "account-ubs-zurich-001",
            "title": "UBS Zurich Account",
            "type": "account",
            "account_type": "bank",
            "institution": "UBS AG",
            "jurisdiction": "Switzerland",
            "holder": "[[cyprus-nominee-corp]]",
            "opened_date": "2005-06-01",
            "closed_date": "2018-12-31",
            "importance": 7,
        }
        body = "Nominee-held account at UBS Zurich, closed after sanctions."
        entry = AccountEntry.from_frontmatter(meta, body)

        assert entry.id == "account-ubs-zurich-001"
        assert entry.account_type == "bank"
        assert entry.institution == "UBS AG"
        assert entry.jurisdiction == "Switzerland"
        assert entry.holder == "[[cyprus-nominee-corp]]"
        assert entry.opened_date == "2005-06-01"
        assert entry.closed_date == "2018-12-31"
        assert entry.body == body

        fm = entry.to_frontmatter()
        assert fm["type"] == "account"
        assert fm["account_type"] == "bank"
        assert fm["institution"] == "UBS AG"
        assert fm["closed_date"] == "2018-12-31"

    def test_defaults(self):
        entry = AccountEntry.from_frontmatter({"title": "Unknown Account"}, "")
        assert entry.account_type == ""
        assert entry.institution == ""
        assert entry.jurisdiction == ""
        assert entry.holder == ""
        assert entry.opened_date == ""
        assert entry.closed_date == ""

    def test_account_type_values(self):
        valid_types = [
            "bank", "brokerage", "crypto_wallet",
            "shell_company", "trust", "other",
        ]
        for account_type in valid_types:
            entry = AccountEntry.from_frontmatter(
                {"title": "Test", "account_type": account_type}, ""
            )
            assert entry.account_type == account_type

    def test_to_frontmatter_omits_empty(self):
        entry = AccountEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "institution" not in fm
        assert "holder" not in fm
        assert "opened_date" not in fm
        assert "closed_date" not in fm


class TestDocumentSourceEntry:
    def test_entry_type(self):
        e = DocumentSourceEntry(id="panama-papers-doc-4427", title="Panama Papers Doc 4427")
        assert e.entry_type == "document_source"

    def test_round_trip(self):
        meta = {
            "id": "panama-papers-doc-4427",
            "title": "Panama Papers Document 4427",
            "type": "document_source",
            "reliability": "high",
            "classification": "leaked",
            "obtained_date": "2016-04-03",
            "obtained_method": "ICIJ database",
            "importance": 9,
            "tags": ["panama-papers", "mossack-fonseca"],
        }
        body = "Mossack Fonseca incorporation document for Cyprus holding."
        entry = DocumentSourceEntry.from_frontmatter(meta, body)

        assert entry.id == "panama-papers-doc-4427"
        assert entry.reliability == "high"
        assert entry.classification == "leaked"
        assert entry.obtained_date == "2016-04-03"
        assert entry.obtained_method == "ICIJ database"
        assert entry.importance == 9
        assert entry.body == body

        fm = entry.to_frontmatter()
        assert fm["type"] == "document_source"
        assert fm["reliability"] == "high"
        assert fm["classification"] == "leaked"

    def test_defaults(self):
        entry = DocumentSourceEntry.from_frontmatter({"title": "Unknown Doc"}, "")
        assert entry.reliability == "unknown"
        assert entry.classification == ""
        assert entry.obtained_date == ""
        assert entry.obtained_method == ""

    def test_reliability_values(self):
        valid = ["high", "medium", "low", "unknown"]
        for r in valid:
            entry = DocumentSourceEntry.from_frontmatter(
                {"title": "Test", "reliability": r}, ""
            )
            assert entry.reliability == r

    def test_classification_values(self):
        valid = [
            "public", "leaked", "foia", "court_filing",
            "financial_disclosure", "corporate_registry", "other",
        ]
        for c in valid:
            entry = DocumentSourceEntry.from_frontmatter(
                {"title": "Test", "classification": c}, ""
            )
            assert entry.classification == c

    def test_to_frontmatter_omits_empty(self):
        entry = DocumentSourceEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "classification" not in fm
        assert "obtained_date" not in fm
        assert "obtained_method" not in fm
