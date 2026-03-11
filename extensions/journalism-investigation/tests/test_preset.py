"""Tests for journalism-investigation KB preset."""

from pyrite_journalism_investigation.preset import JOURNALISM_INVESTIGATION_PRESET


class TestPreset:
    def test_has_name(self):
        assert JOURNALISM_INVESTIGATION_PRESET["name"] == "my-investigation"

    def test_has_description(self):
        assert "investigat" in JOURNALISM_INVESTIGATION_PRESET["description"].lower()

    def test_entity_types_present(self):
        types = JOURNALISM_INVESTIGATION_PRESET["types"]
        assert "asset" in types
        assert "account" in types
        assert "document_source" in types

    def test_event_types_present(self):
        types = JOURNALISM_INVESTIGATION_PRESET["types"]
        assert "investigation_event" in types
        assert "transaction" in types
        assert "legal_action" in types

    def test_claim_type_present(self):
        types = JOURNALISM_INVESTIGATION_PRESET["types"]
        assert "claim" in types
        assert types["claim"]["subdirectory"] == "claims/"

    def test_evidence_type_present(self):
        types = JOURNALISM_INVESTIGATION_PRESET["types"]
        assert "evidence" in types
        assert types["evidence"]["subdirectory"] == "evidence/"

    def test_connection_types_present(self):
        types = JOURNALISM_INVESTIGATION_PRESET["types"]
        assert "ownership" in types
        assert types["ownership"]["subdirectory"] == "connections/"
        assert "membership" in types
        assert types["membership"]["subdirectory"] == "connections/"
        assert "funding" in types
        assert types["funding"]["subdirectory"] == "connections/"

    def test_core_types_present(self):
        """Core types (person, organization) should be in preset for discoverability."""
        types = JOURNALISM_INVESTIGATION_PRESET["types"]
        assert "person" in types
        assert "organization" in types

    def test_subdirectories(self):
        types = JOURNALISM_INVESTIGATION_PRESET["types"]
        assert types["asset"]["subdirectory"] == "entities/"
        assert types["account"]["subdirectory"] == "entities/"
        assert types["document_source"]["subdirectory"] == "sources/"
        assert types["investigation_event"]["subdirectory"] == "events/"
        assert types["transaction"]["subdirectory"] == "events/"
        assert types["legal_action"]["subdirectory"] == "events/"
        assert types["person"]["subdirectory"] == "entities/"
        assert types["organization"]["subdirectory"] == "entities/"

    def test_directories_list(self):
        dirs = JOURNALISM_INVESTIGATION_PRESET["directories"]
        assert "entities" in dirs
        assert "events" in dirs
        assert "sources" in dirs
        assert "claims" in dirs
        assert "evidence" in dirs
        assert "connections" in dirs

    def test_all_types_have_required_fields(self):
        for type_name, type_def in JOURNALISM_INVESTIGATION_PRESET["types"].items():
            assert "required" in type_def, f"{type_name} missing 'required'"
            assert "title" in type_def["required"], f"{type_name} missing 'title' in required"
