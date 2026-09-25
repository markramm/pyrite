"""An entry's version history contains only commits of that entry, and the
KB's confinement to its own subtree fails closed (#432, third round).

Every test here runs against a real git repository: rename pairing,
`--follow` and `rev-parse --show-prefix` are git's behaviour, not ours, and
a mocked output would only restate our assumptions about them.
"""

import logging
import subprocess
from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.git_service import GitService
from pyrite.services.version_service import VersionService
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.models import EntryVersion


def _git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True
    ).stdout.strip()


def _note(entry_id, title, body):
    return f"---\nid: {entry_id}\ntitle: {title}\ntype: note\ntags: [x]\n---\n\n{body}\n"


def _boilerplate_note(entry_id, title, body):
    """Frontmatter heavy enough, and a body short enough, that git's DEFAULT
    rename detection (50%) pairs a delete of one such file with an add of
    another -- the shared boilerplate is most of each file's bytes."""
    return (
        f"---\nid: {entry_id}\ntitle: {title}\ntype: note\nstatus: draft\n"
        "importance: 5\nsources: []\naliases: []\nlifecycle: active\n"
        f"tags:\n- alpha\n- beta\n- gamma\n---\n\n{body}\n"
    )


class _Repo:
    """A git repo with a KB at `repo/<kb_dir>` (or the repo root when
    `kb_dir` is empty), an index, and a VersionService over it."""

    def __init__(self, tmp_path: Path, kb_dir: str = "kb"):
        self.root = tmp_path / "repo"
        self.root.mkdir()
        _git(self.root, "init", "-q")
        _git(self.root, "config", "user.email", "t@example.com")
        _git(self.root, "config", "user.name", "T")
        self.kb = self.root / kb_dir if kb_dir else self.root
        self.kb.mkdir(exist_ok=True)
        self.config = PyriteConfig(
            knowledge_bases=[KBConfig(name="k", path=self.kb)],
            settings=Settings(index_path=tmp_path / "index.db"),
        )
        self.db = PyriteDB(tmp_path / "index.db")
        self.svc = VersionService(self.config, self.db)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, message):
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", message)
        return _git(self.root, "rev-parse", "HEAD")

    def index(self):
        IndexManager(self.db, self.config).index_all()

    def attribute(self):
        IndexManager(self.db, self.config).index_with_attribution("k", GitService)

    def versions(self, entry_id):
        return [
            (v["commit_hash"], v["change_type"]) for v in self.db.get_entry_versions(entry_id, "k")
        ]

    def change_type(self, entry_id, commit):
        row = (
            self.db.session.query(EntryVersion)
            .filter_by(entry_id=entry_id, kb_name="k", commit_hash=commit)
            .first()
        )
        return row.change_type if row else None

    def close(self):
        self.db.close()


@pytest.fixture
def repo(tmp_path):
    r = _Repo(tmp_path)
    yield r
    r.close()


# ---------------------------------------------------------------------------
# 1. A delete plus an unrelated add is not a rename of one entry.
# ---------------------------------------------------------------------------


class TestUnrelatedDeleteAndAddAreNotLinked:
    """`secret.md` deleted and `public.md` added in one commit share only
    frontmatter boilerplate. Linking them serves a deleted entry's content
    as another entry's version, and calls the add a modification."""

    @pytest.fixture
    def m10(self, repo):
        repo.write("kb/secret.md", _note("s1", "Secret", "Private draft: text only s1 has."))
        c_secret = repo.commit("add secret")
        (repo.kb / "secret.md").unlink()
        repo.write("kb/public.md", _note("p1", "Public", "Press release text, nothing else."))
        c_public = repo.commit("delete secret, add public")
        return repo, c_secret, c_public

    def test_file_log_of_the_added_file_starts_at_its_add(self, m10):
        repo, c_secret, c_public = m10
        log = GitService.get_file_log(repo.kb, "public.md")
        assert [e["hash"] for e in log] == [c_public]

    def test_the_add_is_reported_as_an_add(self, m10):
        repo, c_secret, c_public = m10
        statuses = GitService.get_commit_file_statuses(repo.kb, c_public)
        assert ("A", "public.md") in statuses

    def test_attribution_does_not_give_the_new_entry_the_deleted_ones_history(self, m10):
        repo, c_secret, c_public = m10
        repo.index()
        repo.attribute()
        assert repo.versions("p1") == [(c_public, "created")]
        assert repo.svc.get_entry_at_version("p1", "k", c_secret) is None

    def test_record_commit_calls_the_add_created(self, m10):
        repo, c_secret, c_public = m10
        repo.index()
        assert repo.svc.record_commit("k", c_public) == 1
        assert repo.change_type("p1", c_public) == "created"


class TestARenameMustKeepTheEntryId:
    """Frontmatter-heavy notes with short bodies: git's DEFAULT threshold
    pairs the delete of `s2.md` with the add of `p2.md` (checked in the
    fixture). Only the entry id tells a rename from a replacement."""

    @pytest.fixture
    def paired(self, repo):
        repo.write("kb/s2.md", _boilerplate_note("s2", "S", "Alice."))
        c_s2 = repo.commit("add s2")
        (repo.kb / "s2.md").unlink()
        repo.write("kb/p2.md", _boilerplate_note("p2", "P", "Bob."))
        c_p2 = repo.commit("delete s2, add p2")
        status = _git(repo.root, "show", "--name-status", "--format=", c_p2)
        assert status.startswith("R"), f"fixture: git did not pair the files: {status!r}"
        return repo, c_s2, c_p2

    def test_attribution_stops_at_a_rename_that_changes_the_id(self, paired):
        repo, c_s2, c_p2 = paired
        repo.index()
        repo.attribute()
        assert repo.versions("p2") == [(c_p2, "created")]
        assert repo.svc.get_entry_at_version("p2", "k", c_s2) is None

    def test_record_commit_calls_a_rename_that_changes_the_id_created(self, paired):
        repo, c_s2, c_p2 = paired
        repo.index()
        repo.svc.record_commit("k", c_p2)
        assert repo.change_type("p2", c_p2) == "created"

    def test_a_recorded_row_pointing_at_another_entrys_file_is_not_served(self, paired):
        """A row an earlier build recorded (or any row) whose stored path
        holds a different entry at that commit is refused at read time."""
        repo, c_s2, c_p2 = paired
        repo.index()
        repo.db.upsert_entry_version(
            entry_id="p2",
            kb_name="k",
            commit_hash=c_s2,
            author_name="T",
            author_email="t@example.com",
            commit_date="2026-01-01T00:00:00+00:00",
            change_type="created",
            file_path="s2.md",
        )
        assert repo.svc.get_entry_at_version("p2", "k", c_s2) is None

    def test_a_real_rename_keeps_its_history_and_is_a_modification(self, repo):
        repo.write("kb/a.md", _boilerplate_note("e1", "E", "Original body."))
        c1 = repo.commit("add a")
        _git(repo.root, "mv", "kb/a.md", "kb/b.md")
        repo.write("kb/b.md", _boilerplate_note("e1", "E", "Original body, edited."))
        c2 = repo.commit("rename a to b")
        repo.index()
        repo.attribute()
        assert repo.versions("e1") == [(c2, "modified"), (c1, "created")]
        assert "Original body." in repo.svc.get_entry_at_version("e1", "k", c1)

        # record_commit on the rename commit agrees.
        repo.db.session.query(EntryVersion).delete()
        repo.db.session.commit()
        repo.svc.record_commit("k", c2)
        assert repo.change_type("e1", c2) == "modified"


class TestLowSimilarityRenameLimit:
    """Documented limit: a rename bundled with an edit that drops similarity
    below git's default threshold is a new file to git, so the entry's
    history starts at the rename. Its earlier versions are not listed --
    losing them is the price of never linking unrelated files."""

    @pytest.mark.control(
        reason="Documents the accepted limit; it passes on dev too, where "
        "plain --follow already stops at a low-similarity rename."
    )
    def test_history_starts_at_a_low_similarity_rename(self, repo):
        body = [f"line {i}" for i in range(50)]
        repo.write("kb/a.md", _note("e1", "E", "\n".join(body)))
        c1 = repo.commit("add")
        (repo.kb / "a.md").unlink()
        rewritten = [line + " REWRITTEN FROM SCRATCH" for line in body]
        repo.write("kb/z.md", _note("e1", "E", "\n".join(rewritten)))
        c2 = repo.commit("rename with rewrite")
        status = _git(repo.root, "show", "--name-status", "--format=", c2)
        assert not status.startswith("R"), f"fixture: git paired the files: {status!r}"

        hashes = [e["hash"] for e in GitService.get_file_log(repo.kb, "z.md")]
        assert hashes == [c2]
        assert c1 not in hashes


# ---------------------------------------------------------------------------
# 2. Confinement to the KB's subtree fails closed.
# ---------------------------------------------------------------------------


class TestFollowHopsOutsideTheKB:
    """A KB in a subdirectory. `x.md` lived outside the KB (`other/x.md`)
    and was moved in; `git log --follow` walks back to the outside path.

    The KB also held a file at `kb/other/x.md` with the same id before the
    move: without the refusal, the outside path `other/x.md` is taken as
    KB-relative and resolves to that file, so even the id check passes --
    only the refusal stands between the outside history and this KB."""

    @pytest.fixture
    def hop(self, repo):
        repo.write("other/x.md", _note("x1", "X", "Outside the KB."))
        repo.write("kb/other/x.md", _note("x1", "X", "An older copy inside the KB."))
        c0 = repo.commit("outside file, and an in-KB namesake")
        _git(repo.root, "mv", "other/x.md", "kb/x.md")
        _git(repo.root, "rm", "-q", "kb/other/x.md")
        c1 = repo.commit("move x into the KB")
        status = _git(repo.root, "log", "--follow", "--format=%H", "--", "kb/x.md")
        assert c0 in status, "fixture: --follow did not reach the outside path"
        return repo, c0, c1

    def test_file_log_drops_the_outside_commit(self, hop):
        repo, c0, c1 = hop
        log = GitService.get_file_log(repo.kb, "x.md")
        assert [(e["hash"], e["file_path"]) for e in log] == [(c1, "x.md")]

    def test_attribution_records_only_the_in_kb_commit(self, hop):
        repo, c0, c1 = hop
        repo.index()
        repo.attribute()
        assert repo.versions("x1") == [(c1, "created")]
        assert repo.svc.get_entry_at_version("x1", "k", c0) is None


class TestKbPrefixFailsClosed:
    def test_prefix_is_none_when_rev_parse_fails(self, tmp_path):
        not_a_repo = tmp_path / "plain"
        not_a_repo.mkdir()
        assert GitService.get_kb_prefix(not_a_repo) is None

    def test_no_prefix_means_no_paths(self, repo, monkeypatch):
        repo.write("kb/a.md", _note("a1", "A", "a"))
        c = repo.commit("a")
        monkeypatch.setattr(GitService, "get_kb_prefix", staticmethod(lambda _path: None))
        assert GitService.get_file_log(repo.kb, "a.md") == []
        assert GitService.get_commit_file_statuses(repo.kb, c) == []

    def test_a_leading_space_in_the_kb_directory_is_kept(self, tmp_path):
        """`" kb"` and `"kb"` are different directories; stripping the
        prefix's whitespace would make `kb/` files look like `" kb"`'s."""
        r = _Repo(tmp_path, kb_dir=" kb")
        try:
            r.write(" kb/own.md", _note("o1", "O", "own"))
            r.commit("own")
            r.write("kb/a.md", _note("a1", "A", "a sibling's file"))
            c = r.commit("sibling")
            assert GitService.get_kb_prefix(r.kb) == " kb/"
            assert GitService.get_commit_files(r.kb, c) == []
            assert GitService.get_file_log(r.kb, "a.md") == []
        finally:
            r.close()


class TestStoredPathShapeIsRefusedAtReadTime:
    """A stored version path is KB-relative. One that climbs out of the KB
    (`..`) or is absolute is refused, not resolved. Each file below carries
    the entry's own id, so only the shape check refuses it."""

    @pytest.fixture
    def stored(self, repo):
        repo.write("kb/a.md", _note("e1", "E", "current"))
        repo.write("outside.md", _note("e1", "E", "OUTSIDE THE KB"))
        repo.write("kb/b.md", _note("e1", "E", "A FILE THE ROW DOES NOT NAME"))
        c = repo.commit("files")
        (repo.kb / "b.md").unlink()
        repo.commit("drop b")
        repo.index()

        def read_with_stored_path(path):
            repo.db.upsert_entry_version(
                entry_id="e1",
                kb_name="k",
                commit_hash=c,
                author_name="T",
                author_email="t@example.com",
                commit_date="2026-01-01T00:00:00+00:00",
                change_type="modified",
                file_path=path,
            )
            return repo.svc.get_entry_at_version("e1", "k", c)

        return read_with_stored_path

    def test_parent_segments_are_refused(self, stored):
        assert stored("../outside.md") is None

    def test_parent_segments_inside_the_kb_are_refused(self, stored):
        assert stored("sub/../b.md") is None

    def test_an_absolute_path_outside_the_kb_is_refused(self, stored):
        # git anchors "./" + "/b.md" inside the KB, reading kb/b.md.
        assert stored("/b.md") is None


# ---------------------------------------------------------------------------
# 3. record_commit skips a bad index row, not the whole commit.
# ---------------------------------------------------------------------------


class TestRecordCommitSkipsABadIndexRow:
    @pytest.mark.parametrize("bad_path", ["", "/somewhere/else/z.md"])
    def test_other_entries_are_still_recorded(self, repo, caplog, bad_path):
        repo.write("kb/a.md", _note("a1", "A", "a"))
        repo.index()
        repo.db.upsert_entry(
            {
                "id": "bad",
                "kb_name": "k",
                "entry_type": "note",
                "title": "Bad",
                "body": "",
                "file_path": bad_path,
            }
        )
        c = repo.commit("a")
        with caplog.at_level(logging.WARNING):
            assert repo.svc.record_commit("k", c) == 1
        assert repo.db.entry_version_exists("a1", "k", c)
        assert "bad" in caplog.text


class TestReadFileAtRefusesUnsafePaths:
    def test_read_file_at_refuses_parent_and_absolute_paths(self, repo):
        repo.write("kb/a.md", _note("a1", "A", "inside"))
        repo.write("outside.md", _note("a1", "A", "outside"))
        c = repo.commit("files")
        assert GitService.read_file_at(repo.kb, c, "a.md") is not None
        assert GitService.read_file_at(repo.kb, c, "../outside.md") is None
        assert GitService.read_file_at(repo.kb, c, "/a.md") is None

    def test_an_index_path_outside_the_kb_is_not_read_as_a_kb_file(self, repo):
        """An entry whose indexed path is not under the KB, with a version
        row that has no stored path, has no KB-relative path to read: it is
        refused, not read at some stand-in name inside the KB."""
        repo.write("kb/None", "not an entry\n")
        c = repo.commit("a file named None")
        repo.index()
        repo.db.upsert_entry(
            {
                "id": "stray",
                "kb_name": "k",
                "entry_type": "note",
                "title": "Stray",
                "body": "",
                "file_path": "/somewhere/else/stray.md",
            }
        )
        repo.db.upsert_entry_version(
            entry_id="stray",
            kb_name="k",
            commit_hash=c,
            author_name="T",
            author_email="t@example.com",
            commit_date="2026-01-01T00:00:00+00:00",
        )
        assert repo.svc.get_entry_at_version("stray", "k", c) is None
