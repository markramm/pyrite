"""Tests for actor alias suggestion and fuzzy matching pipeline."""

from collections import Counter

import pytest

from pyrite_cascade.aliases import (
    AliasProposal,
    apply_proposals,
    extract_actor_counts_from_db,
    find_acronym_duplicates,
    find_case_duplicates,
    find_fuzzy_duplicates,
    find_parenthetical_duplicates,
    find_prefix_duplicates,
    find_slug_duplicates,
    pick_canonical,
    run_detection,
    slugify,
    strip_parenthetical,
    strip_prefix,
)


class TestSlugify:
    def test_basic(self):
        assert slugify("Donald Trump") == "donald-trump"

    def test_possessive(self):
        assert slugify("Trump's DOJ") == "trumps-doj"

    def test_unicode(self):
        assert slugify("François Hollande") == "francois-hollande"

    def test_punctuation(self):
        assert slugify("U.S. Department of Justice") == "u-s-department-of-justice"


class TestStripPrefix:
    def test_us_prefix(self):
        assert strip_prefix("US Department of Justice") == "Department of Justice"

    def test_us_dot_prefix(self):
        assert strip_prefix("U.S. Department of Justice") == "Department of Justice"

    def test_united_states_prefix(self):
        assert strip_prefix("United States Senate") == "Senate"

    def test_no_prefix(self):
        assert strip_prefix("FBI") is None


class TestStripParenthetical:
    def test_with_acronym(self):
        base, acr = strip_parenthetical("Federal Bureau of Investigation (FBI)")
        assert base == "Federal Bureau of Investigation"
        assert acr == "FBI"

    def test_no_parens(self):
        base, acr = strip_parenthetical("Donald Trump")
        assert base is None
        assert acr is None


class TestPickCanonical:
    def test_prefers_full_name_over_acronym(self):
        names = ["FBI", "Federal Bureau of Investigation"]
        counts = {"FBI": 100, "Federal Bureau of Investigation": 5}
        assert pick_canonical(names, counts) == "Federal Bureau of Investigation"

    def test_prefers_no_prefix(self):
        names = ["U.S. Senate", "Senate"]
        counts = {"U.S. Senate": 10, "Senate": 50}
        assert pick_canonical(names, counts) == "Senate"

    def test_prefers_proper_case(self):
        names = ["donald trump", "Donald Trump"]
        counts = {"donald trump": 5, "Donald Trump": 50}
        assert pick_canonical(names, counts) == "Donald Trump"


class TestFindCaseDuplicates:
    def test_finds_case_variants(self):
        actors = ["Donald Trump", "donald trump", "DONALD TRUMP"]
        counts = {"Donald Trump": 100, "donald trump": 5, "DONALD TRUMP": 2}
        proposals, matched = find_case_duplicates(actors, counts)
        assert len(proposals) == 1
        assert proposals[0].canonical == "Donald Trump"
        assert set(proposals[0].aliases) == {"donald trump", "DONALD TRUMP"}
        assert proposals[0].confidence == 100

    def test_no_duplicates(self):
        actors = ["Donald Trump", "Joe Biden"]
        counts = {"Donald Trump": 100, "Joe Biden": 50}
        proposals, matched = find_case_duplicates(actors, counts)
        assert len(proposals) == 0


class TestFindSlugDuplicates:
    def test_possessive_match(self):
        actors = ["Trump's DOJ", "Trumps DOJ"]
        counts = {"Trump's DOJ": 10, "Trumps DOJ": 5}
        proposals, matched = find_slug_duplicates(actors, counts)
        assert len(proposals) == 1
        assert proposals[0].confidence == 95


class TestFindPrefixDuplicates:
    def test_us_prefix(self):
        actors = ["U.S. Senate", "Senate"]
        counts = {"U.S. Senate": 10, "Senate": 50}
        proposals, matched = find_prefix_duplicates(actors, counts)
        assert len(proposals) == 1
        assert proposals[0].canonical == "Senate"


class TestFindParentheticalDuplicates:
    def test_acronym_in_parens(self):
        actors = ["Federal Bureau of Investigation (FBI)", "FBI",
                   "Federal Bureau of Investigation"]
        counts = {"Federal Bureau of Investigation (FBI)": 5, "FBI": 80,
                  "Federal Bureau of Investigation": 20}
        proposals, matched = find_parenthetical_duplicates(actors, counts)
        assert len(proposals) == 1
        assert proposals[0].canonical == "Federal Bureau of Investigation"


class TestFindAcronymDuplicates:
    def test_known_acronym(self):
        actors = ["FBI", "Federal Bureau of Investigation"]
        counts = {"FBI": 100, "Federal Bureau of Investigation": 5}
        proposals, matched = find_acronym_duplicates(actors, counts)
        assert len(proposals) == 1
        assert proposals[0].canonical == "Federal Bureau of Investigation"
        assert "FBI" in proposals[0].aliases

    def test_no_match_when_full_name_absent(self):
        actors = ["FBI"]
        counts = {"FBI": 100}
        proposals, matched = find_acronym_duplicates(actors, counts)
        assert len(proposals) == 0


class TestFindFuzzyDuplicates:
    def test_similar_names(self):
        # Names must share a first word (fuzzy groups by first word)
        actors = ["Peter Hegseth", "Peter Hegsteth"]
        counts = {"Peter Hegseth": 50, "Peter Hegsteth": 10}
        proposals, matched = find_fuzzy_duplicates(actors, counts, min_count=2)
        assert len(proposals) == 1
        assert proposals[0].strategy == "fuzzy"

    def test_different_names_no_match(self):
        actors = ["Donald Trump", "Joe Biden"]
        counts = {"Donald Trump": 100, "Joe Biden": 50}
        proposals, matched = find_fuzzy_duplicates(actors, counts, min_count=2)
        assert len(proposals) == 0


class TestRunDetection:
    def test_full_pipeline(self):
        actor_counts = Counter({
            "Donald Trump": 500,
            "donald trump": 3,
            "FBI": 100,
            "Federal Bureau of Investigation": 20,
            "U.S. Senate": 30,
            "Senate": 50,
            "Pete Hegseth": 40,
            "Peter Hegseth": 5,
            "Joe Biden": 200,
        })
        proposals = run_detection(actor_counts)
        assert len(proposals) >= 3
        canonicals = {p.canonical for p in proposals}
        # Case-insensitive should catch Donald Trump
        assert "Donald Trump" in canonicals
        # Some strategy should group FBI/Federal Bureau
        fbi_proposal = next(
            (p for p in proposals
             if "FBI" in [p.canonical] + p.aliases
             or "Federal Bureau of Investigation" in [p.canonical] + p.aliases),
            None,
        )
        assert fbi_proposal is not None

    def test_empty_input(self):
        proposals = run_detection({})
        assert proposals == []

    def test_no_duplicates(self):
        actor_counts = Counter({"Alpha": 10, "Beta": 20, "Gamma": 30})
        proposals = run_detection(actor_counts)
        assert len(proposals) == 0


class TestApplyProposals:
    def test_auto_accept_above_threshold(self):
        proposals = [
            AliasProposal("Donald Trump", ["donald trump"], "exact-case", 100),
            AliasProposal("FBI", ["Federal Bureau of Investigation"], "known-acronym", 85),
            AliasProposal("Pete Hegseth", ["Peter Hegseth"], "fuzzy", 88),
        ]
        result = apply_proposals(proposals, min_confidence=90)
        assert "Donald Trump" in result
        assert "FBI" not in result  # 85 < 90

    def test_conflict_resolution(self):
        proposals = [
            AliasProposal("A", ["B"], "test", 100),
            AliasProposal("B", ["C"], "test", 95),  # conflicts with first (B used)
        ]
        result = apply_proposals(proposals, min_confidence=0)
        assert "A" in result
        assert "B" not in result  # skipped due to conflict


class TestExtractActorCountsFromDB:
    def test_extracts_from_events(self, tmp_path):
        from pyrite.config import PyriteConfig, Settings, KBConfig
        from pyrite.storage.database import PyriteDB
        from pyrite.services.kb_service import KBService

        kb_path = tmp_path / "test-kb"
        kb_path.mkdir()
        kb = KBConfig(name="test", path=kb_path, kb_type="cascade-timeline")
        config = PyriteConfig(
            knowledge_bases=[kb],
            settings=Settings(index_path=tmp_path / "index.db"),
        )
        db = PyriteDB(tmp_path / "index.db")
        svc = KBService(config, db)

        svc.create_entry("test", "e1", "Event 1", "timeline_event",
                         date="2025-01-01", actors=["Donald Trump", "FBI"])
        svc.create_entry("test", "e2", "Event 2", "timeline_event",
                         date="2025-02-01", actors=["Donald Trump", "Elon Musk"])

        counts = extract_actor_counts_from_db(db, "test")
        assert counts["Donald Trump"] == 2
        assert counts["FBI"] == 1
        assert counts["Elon Musk"] == 1

        db.close()
