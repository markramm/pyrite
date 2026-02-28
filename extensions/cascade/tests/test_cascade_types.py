"""Round-trip tests for Cascade Series entry types."""


from pyrite_cascade.entry_types import (
    ActorEntry,
    CascadeEventEntry,
    CascadeOrgEntry,
    MechanismEntry,
    SceneEntry,
    SolidarityEventEntry,
    StatisticEntry,
    ThemeEntry,
    TimelineEventEntry,
    VictimEntry,
)


class TestActorEntry:
    def test_entry_type(self):
        e = ActorEntry(id="powell-lewis", title="Lewis Powell")
        assert e.entry_type == "actor"

    def test_round_trip(self):
        meta = {
            "id": "powell-lewis",
            "title": "Lewis Powell",
            "type": "actor",
            "role": "architect",
            "era": "1971-1987",
            "importance": 10,
            "tier": 1,
            "capture_lanes": ["judicial", "political"],
            "chapters": [1, 5],
            "tags": ["powell-memo", "supreme-court"],
            "research_status": "in-progress",
        }
        body = "## Quick Facts\nArchitect of corporate capture."
        entry = ActorEntry.from_frontmatter(meta, body)

        assert entry.id == "powell-lewis"
        assert entry.role == "architect"
        assert entry.era == "1971-1987"
        assert entry.importance == 10
        assert entry.tier == 1
        assert entry.capture_lanes == ["judicial", "political"]
        assert entry.chapters == [1, 5]
        assert entry.body == body

        fm = entry.to_frontmatter()
        assert fm["type"] == "actor"
        assert fm["tier"] == 1
        assert fm["era"] == "1971-1987"
        assert fm["capture_lanes"] == ["judicial", "political"]

    def test_defaults(self):
        entry = ActorEntry.from_frontmatter({"title": "Nobody"}, "")
        assert entry.tier == 0
        assert entry.era == ""
        assert entry.capture_lanes == []
        assert entry.chapters == []


class TestCascadeOrgEntry:
    def test_entry_type(self):
        e = CascadeOrgEntry(id="heritage", title="Heritage Foundation")
        assert e.entry_type == "cascade_org"

    def test_round_trip(self):
        meta = {
            "id": "heritage-foundation",
            "title": "Heritage Foundation",
            "type": "cascade_org",
            "founded": "1973-02-16",
            "importance": 10,
            "capture_lanes": ["political", "judicial"],
            "chapters": [1, 4],
            "tags": ["think-tank"],
        }
        entry = CascadeOrgEntry.from_frontmatter(meta, "Policy pipeline.")
        assert entry.founded == "1973-02-16"
        assert entry.capture_lanes == ["political", "judicial"]

        fm = entry.to_frontmatter()
        assert fm["type"] == "cascade_org"
        assert fm["founded"] == "1973-02-16"


class TestCascadeEventEntry:
    def test_entry_type(self):
        e = CascadeEventEntry(id="j6", title="January 6")
        assert e.entry_type == "cascade_event"

    def test_round_trip(self):
        meta = {
            "id": "january-6",
            "title": "January 6 Insurrection",
            "type": "cascade_event",
            "event_date": "2021-01-06",
            "era": "2020-2024",
            "importance": 10,
            "capture_lanes": ["electoral-capture"],
            "chapters": [16],
        }
        entry = CascadeEventEntry.from_frontmatter(meta, "Insurrection.")
        assert entry.date == "2021-01-06"
        assert entry.era == "2020-2024"

        fm = entry.to_frontmatter()
        assert fm["type"] == "cascade_event"


class TestTimelineEventEntry:
    def test_entry_type(self):
        e = TimelineEventEntry(id="test", title="Test Event")
        assert e.entry_type == "timeline_event"

    def test_round_trip(self):
        meta = {
            "id": "2022-04-01--heritage-project-2025",
            "title": "Heritage Foundation Launches Project 2025",
            "type": "timeline_event",
            "date": "2022-04-01",
            "importance": 9,
            "actors": ["Heritage Foundation", "Kevin Roberts"],
            "capture_lanes": ["Executive Power Expansion"],
            "capture_type": "institutional_capture",
            "tags": ["project-2025"],
            "sources": [
                {"title": "Heritage Announces 2025", "url": "https://example.com"}
            ],
        }
        entry = TimelineEventEntry.from_frontmatter(meta, "Heritage launched P2025.")
        assert entry.date == "2022-04-01"
        assert entry.actors == ["Heritage Foundation", "Kevin Roberts"]
        assert entry.capture_type == "institutional_capture"
        assert entry.capture_lanes == ["Executive Power Expansion"]

        fm = entry.to_frontmatter()
        assert fm["type"] == "timeline_event"
        assert fm["actors"] == ["Heritage Foundation", "Kevin Roberts"]
        assert fm["capture_type"] == "institutional_capture"

    def test_quoted_date_stripped(self):
        """Date values with YAML quotes should be stripped."""
        meta = {"id": "test", "title": "Test", "date": "'2024-01-15'"}
        entry = TimelineEventEntry.from_frontmatter(meta, "")
        assert entry.date == "2024-01-15"


class TestSolidarityEventEntry:
    def test_entry_type(self):
        e = SolidarityEventEntry(id="test", title="Test Solidarity Event")
        assert e.entry_type == "solidarity_event"

    def test_round_trip(self):
        meta = {
            "id": "1831-01-01--the-liberator-launch",
            "title": "William Lloyd Garrison Launches The Liberator",
            "type": "solidarity_event",
            "date": "1831-01-01",
            "importance": 9,
            "infrastructure_types": ["Direct Action and Exposure", "Cultural Resistance"],
            "actors": ["William Lloyd Garrison", "Isaac Knapp", "Free Black subscribers"],
            "location": "Boston, Massachusetts",
            "lineage": ["1827-03-16--freedoms-journal-first-black-newspaper"],
            "lineage_notes": "Built on Freedom's Journal model but with radical immediatist stance",
            "legacy": ["1847-12-03--north-star-launch"],
            "legacy_notes": "Template for abolitionist press network",
            "capture_response": ["1830-04-06--indian-removal-act"],
            "outcome": "Published weekly for 35 years. Radicalized northern opinion.",
            "status": "confirmed",
            "tags": ["abolitionist-press", "publication-networks"],
            "sources": [
                {"title": "All on Fire: William Lloyd Garrison", "url": ""}
            ],
        }
        entry = SolidarityEventEntry.from_frontmatter(meta, "The Liberator body.")
        assert entry.date == "1831-01-01"
        assert entry.importance == 9
        assert entry.infrastructure_types == ["Direct Action and Exposure", "Cultural Resistance"]
        assert entry.actors == ["William Lloyd Garrison", "Isaac Knapp", "Free Black subscribers"]
        assert entry.location == "Boston, Massachusetts"
        assert entry.lineage == ["1827-03-16--freedoms-journal-first-black-newspaper"]
        assert entry.lineage_notes == "Built on Freedom's Journal model but with radical immediatist stance"
        assert entry.legacy == ["1847-12-03--north-star-launch"]
        assert entry.legacy_notes == "Template for abolitionist press network"
        assert entry.capture_response == ["1830-04-06--indian-removal-act"]
        assert entry.outcome == "Published weekly for 35 years. Radicalized northern opinion."

        fm = entry.to_frontmatter()
        assert fm["type"] == "solidarity_event"
        assert fm["infrastructure_types"] == ["Direct Action and Exposure", "Cultural Resistance"]
        assert fm["actors"] == ["William Lloyd Garrison", "Isaac Knapp", "Free Black subscribers"]
        assert fm["lineage"] == ["1827-03-16--freedoms-journal-first-black-newspaper"]
        assert fm["legacy"] == ["1847-12-03--north-star-launch"]
        assert fm["capture_response"] == ["1830-04-06--indian-removal-act"]
        assert fm["outcome"] == "Published weekly for 35 years. Radicalized northern opinion."

    def test_defaults(self):
        entry = SolidarityEventEntry.from_frontmatter({"title": "Minimal Event"}, "")
        assert entry.infrastructure_types == []
        assert entry.actors == []
        assert entry.lineage == []
        assert entry.lineage_notes == ""
        assert entry.legacy == []
        assert entry.legacy_notes == ""
        assert entry.capture_response == []
        assert entry.outcome == ""


class TestThemeEntry:
    def test_entry_type(self):
        e = ThemeEntry(id="test", title="Test Theme")
        assert e.entry_type == "theme"

    def test_round_trip(self):
        meta = {
            "id": "christian-nationalism",
            "title": "Christian Nationalism",
            "type": "theme",
            "importance": 9,
            "research_status": "comprehensive",
            "tags": ["christian-nationalism"],
        }
        entry = ThemeEntry.from_frontmatter(meta, "Theme body.")
        assert entry.research_status == "comprehensive"
        assert entry.importance == 9

        fm = entry.to_frontmatter()
        assert fm["type"] == "theme"
        assert fm["research_status"] == "comprehensive"


class TestVictimEntry:
    def test_round_trip(self):
        meta = {
            "id": "16th-street-victims",
            "title": "16th Street Baptist Church Victims",
            "type": "victim",
            "era": "1963",
            "location": "Birmingham, Alabama",
            "importance": 10,
            "research_status": "comprehensive",
        }
        entry = VictimEntry.from_frontmatter(meta, "Four girls.")
        assert entry.entry_type == "victim"
        assert entry.era == "1963"
        assert entry.location == "Birmingham, Alabama"

        fm = entry.to_frontmatter()
        assert fm["type"] == "victim"
        assert fm["location"] == "Birmingham, Alabama"


class TestStatisticEntry:
    def test_round_trip(self):
        meta = {
            "id": "pac-growth",
            "title": "Corporate PAC Growth",
            "type": "statistic",
            "era": "1974-1980",
            "data_type": "political",
            "verified": True,
            "importance": 8,
            "research_status": "in-progress",
        }
        entry = StatisticEntry.from_frontmatter(meta, "89 to 1,206.")
        assert entry.entry_type == "statistic"
        assert entry.verified is True
        assert entry.data_type == "political"

        fm = entry.to_frontmatter()
        assert fm["type"] == "statistic"
        assert fm["verified"] is True


class TestMechanismEntry:
    def test_round_trip(self):
        meta = {
            "id": "electoral-manipulation",
            "title": "Electoral Manipulation",
            "type": "mechanism",
            "importance": 10,
            "related_orgs": ["ALEC", "Federalist Society"],
            "related_actors": ["Powell"],
            "chapters": [10, 16],
        }
        entry = MechanismEntry.from_frontmatter(meta, "Four mechanisms.")
        assert entry.entry_type == "mechanism"
        assert entry.related_orgs == ["ALEC", "Federalist Society"]
        assert entry.chapters == [10, 16]

        fm = entry.to_frontmatter()
        assert fm["type"] == "mechanism"
        assert fm["related_orgs"] == ["ALEC", "Federalist Society"]


class TestSceneEntry:
    def test_round_trip(self):
        meta = {
            "id": "ford-pardon",
            "title": "The Eleven Minutes",
            "type": "scene",
            "scene_date": "1974-09-08",
            "era": "1974-1977",
            "related_events": ["1974-09-08-ford-pardon"],
            "actors": ["gerald-ford", "richard-nixon"],
            "importance": 10,
        }
        entry = SceneEntry.from_frontmatter(meta, "Scene body.")
        assert entry.entry_type == "scene"
        assert entry.scene_date == "1974-09-08"
        assert entry.actors == ["gerald-ford", "richard-nixon"]

        fm = entry.to_frontmatter()
        assert fm["type"] == "scene"
        assert fm["scene_date"] == "1974-09-08"


class TestGenericPassthrough:
    """Low-count types (analysis, source, synthesis, etc.) should work via GenericEntry."""

    def test_analysis_loads_as_generic(self):
        from pyrite.models.core_types import entry_from_frontmatter

        meta = {
            "id": "test-analysis",
            "title": "Test Analysis",
            "type": "analysis",
            "era": "2020",
            "custom_field": "value",
        }
        entry = entry_from_frontmatter(meta, "Analysis body.")
        assert entry.entry_type == "analysis"
        assert entry.metadata.get("era") == "2020"
        assert entry.metadata.get("custom_field") == "value"
