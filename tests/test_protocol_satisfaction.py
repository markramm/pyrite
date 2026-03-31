"""Tests for protocol versioning and satisfaction checking."""

import dataclasses
from dataclasses import dataclass

import pytest

from pyrite.models.protocols import (
    PROTOCOL_REGISTRY,
    Assignable,
    Locatable,
    Parentable,
    Prioritizable,
    ProtocolCheckResult,
    Statusable,
    Temporal,
    check_protocol_satisfaction,
    get_all_protocol_info,
    get_protocol_info,
)


class TestProtocolVersions:
    """Every protocol has a PROTOCOL_VERSION ClassVar."""

    def test_all_protocols_have_version(self):
        for name, cls in PROTOCOL_REGISTRY.items():
            assert hasattr(cls, "PROTOCOL_VERSION"), f"{name} missing PROTOCOL_VERSION"
            assert isinstance(cls.PROTOCOL_VERSION, int)
            assert cls.PROTOCOL_VERSION >= 1

    def test_version_not_in_dataclass_fields(self):
        for name, cls in PROTOCOL_REGISTRY.items():
            field_names = {f.name for f in dataclasses.fields(cls)}
            assert "PROTOCOL_VERSION" not in field_names, (
                f"{name}.PROTOCOL_VERSION should be ClassVar, not a field"
            )

    def test_six_protocols_registered(self):
        assert len(PROTOCOL_REGISTRY) == 6
        expected = {"assignable", "temporal", "locatable", "statusable", "prioritizable", "parentable"}
        assert set(PROTOCOL_REGISTRY.keys()) == expected


class TestProtocolInfo:
    def test_get_protocol_info_temporal(self):
        info = get_protocol_info("temporal")
        assert info is not None
        assert info["version"] == 1
        assert set(info["fields"]) == {"date", "start_date", "end_date", "due_date"}
        assert info["mixin_class"] is Temporal

    def test_get_protocol_info_assignable(self):
        info = get_protocol_info("assignable")
        assert info is not None
        assert set(info["fields"]) == {"assignee", "assigned_at"}

    def test_get_protocol_info_unknown(self):
        assert get_protocol_info("nonexistent") is None

    def test_get_all_protocol_info(self):
        all_info = get_all_protocol_info()
        assert len(all_info) == 6
        assert "assignable" in all_info
        assert "parentable" in all_info
        for _name, info in all_info.items():
            assert info["version"] >= 1
            assert len(info["fields"]) >= 1


class TestNominalSatisfaction:
    """Types that inherit the mixin satisfy the protocol nominally."""

    def test_event_satisfies_temporal(self):
        from pyrite.models.core_types import EventEntry

        results = check_protocol_satisfaction(EventEntry, ["temporal"])
        assert len(results) == 1
        assert results[0].satisfied is True
        assert results[0].method == "nominal"

    def test_event_satisfies_all_declared(self):
        from pyrite.models.core_types import EventEntry

        results = check_protocol_satisfaction(
            EventEntry, ["temporal", "locatable", "statusable"]
        )
        assert all(r.satisfied for r in results)
        assert all(r.method == "nominal" for r in results)

    def test_person_satisfies_locatable(self):
        from pyrite.models.core_types import PersonEntry

        results = check_protocol_satisfaction(PersonEntry, ["locatable"])
        assert results[0].satisfied is True
        assert results[0].method == "nominal"

    def test_note_does_not_satisfy_temporal(self):
        from pyrite.models.core_types import NoteEntry

        results = check_protocol_satisfaction(NoteEntry, ["temporal"])
        assert results[0].satisfied is False
        assert "date" in results[0].missing_fields

    def test_document_satisfies_temporal(self):
        from pyrite.models.core_types import DocumentEntry

        results = check_protocol_satisfaction(DocumentEntry, ["temporal"])
        assert results[0].satisfied is True


class TestStructuralSatisfaction:
    """Types with matching fields (but no inheritance) satisfy structurally."""

    def test_custom_class_with_matching_fields(self):
        @dataclass
        class CustomEntry:
            status: str = ""

        results = check_protocol_satisfaction(CustomEntry, ["statusable"])
        assert results[0].satisfied is True
        assert results[0].method == "structural"

    def test_custom_class_with_all_temporal_fields(self):
        @dataclass
        class CustomTemporal:
            date: str = ""
            start_date: str = ""
            end_date: str = ""
            due_date: str = ""

        results = check_protocol_satisfaction(CustomTemporal, ["temporal"])
        assert results[0].satisfied is True
        assert results[0].method == "structural"

    def test_custom_class_missing_fields(self):
        @dataclass
        class PartialEntry:
            location: str = ""
            # Missing: coordinates

        results = check_protocol_satisfaction(PartialEntry, ["locatable"])
        assert results[0].satisfied is False
        assert "coordinates" in results[0].missing_fields


class TestSchemaSatisfaction:
    """GenericEntry types checked via TypeSchema fields."""

    def test_schema_with_matching_fields(self):
        from pyrite.models.generic import GenericEntry
        from pyrite.schema.field_schema import FieldSchema, TypeSchema

        ts = TypeSchema(
            name="meeting",
            fields={
                "date": FieldSchema(name="date"),
                "start_date": FieldSchema(name="start_date"),
                "end_date": FieldSchema(name="end_date"),
                "due_date": FieldSchema(name="due_date"),
            },
        )
        results = check_protocol_satisfaction(GenericEntry, ["temporal"], ts)
        assert results[0].satisfied is True
        assert results[0].method == "schema"

    def test_schema_with_fields_in_optional(self):
        from pyrite.models.generic import GenericEntry
        from pyrite.schema.field_schema import TypeSchema

        ts = TypeSchema(
            name="record",
            optional=["status"],
        )
        results = check_protocol_satisfaction(GenericEntry, ["statusable"], ts)
        assert results[0].satisfied is True
        assert results[0].method == "schema"

    def test_schema_missing_fields(self):
        from pyrite.models.generic import GenericEntry
        from pyrite.schema.field_schema import TypeSchema

        ts = TypeSchema(name="meeting", fields={})
        results = check_protocol_satisfaction(GenericEntry, ["temporal"], ts)
        assert results[0].satisfied is False
        assert len(results[0].missing_fields) == 4


class TestUnknownProtocol:
    def test_unknown_protocol_name(self):
        from pyrite.models.core_types import NoteEntry

        results = check_protocol_satisfaction(NoteEntry, ["nonexistent_protocol"])
        assert results[0].satisfied is False
        assert "Unknown protocol" in results[0].message
        assert results[0].method == "unknown"


class TestMultipleProtocols:
    def test_mixed_pass_fail(self):
        from pyrite.models.core_types import PersonEntry

        results = check_protocol_satisfaction(PersonEntry, ["locatable", "temporal"])
        assert results[0].satisfied is True  # locatable: PersonEntry inherits Locatable
        assert results[1].satisfied is False  # temporal: PersonEntry does not have Temporal

    def test_empty_protocol_list(self):
        from pyrite.models.core_types import NoteEntry

        results = check_protocol_satisfaction(NoteEntry, [])
        assert results == []

    def test_all_pass(self):
        from pyrite.models.core_types import EventEntry

        results = check_protocol_satisfaction(
            EventEntry, ["temporal", "locatable", "statusable"]
        )
        assert len(results) == 3
        assert all(r.satisfied for r in results)


class TestProtocolCheckResult:
    def test_result_fields(self):
        r = ProtocolCheckResult(
            protocol_name="temporal",
            type_name="EventEntry",
            satisfied=True,
            method="nominal",
        )
        assert r.missing_fields == []
        assert r.message == ""

    def test_result_with_failures(self):
        r = ProtocolCheckResult(
            protocol_name="temporal",
            type_name="NoteEntry",
            satisfied=False,
            method="structural",
            missing_fields=["date", "start_date"],
            message="Missing fields",
        )
        assert not r.satisfied
        assert len(r.missing_fields) == 2
