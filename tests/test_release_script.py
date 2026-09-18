"""Tests for scripts/release.py -- the one command from a CI-verified `dev`
commit to a GitHub release.

v0.24.1 took ten manual steps across two sessions, one of which pushed with
`--no-verify` because the pre-push hooks ran fixers over the wrong range. The
script mechanizes the runbook; these tests pin the parts that must be right
before anything irreversible runs:

- the preconditions (version, CHANGELOG shape, clean checkout at origin/dev)
- notes extraction (the CHANGELOG section, the contributors line)
- the CI-status decision, given mocked `gh` JSON
- step ordering: no irreversible step precedes a check
- the safety rules: no --no-verify, no force push, no delete, and --dry-run
  as the default

No test performs network or git pushes. The `--dry-run` pass over this repo
runs with every subprocess call monkeypatched.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import release  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# fixtures: a good checkout, and each way it can be wrong
# --------------------------------------------------------------------------

GOOD_CHANGELOG = """# Changelog

All notable changes to Pyrite will be documented in this file.

## [Unreleased]

## [0.24.2] - {today} - Operational

### Added

- A release script.

## [0.24.1] - 2026-09-17

### Fixed

- Something older.
"""

GOOD_PYPROJECT = """[project]
name = "pyrite"
version = "0.24.2"
"""


@pytest.fixture
def repo(tmp_path):
    """A tmp checkout whose CHANGELOG and pyproject are release-ready."""
    (tmp_path / "CHANGELOG.md").write_text(GOOD_CHANGELOG.format(today=date.today().isoformat()))
    (tmp_path / "pyproject.toml").write_text(GOOD_PYPROJECT)
    return tmp_path


FAKE_SHA = "abc1234def5678"


@pytest.fixture
def no_network(monkeypatch):
    """Every external call stubbed. Returns the list of commands attempted, so
    a test can assert that a dry run shells out only to reads."""
    calls = []

    def fake_check_output(cmd, **kwargs):
        calls.append(list(cmd))
        joined = " ".join(cmd)
        if "status --porcelain" in joined:
            return ""
        if "rev-parse --abbrev-ref" in joined:
            return "dev"
        if "rev-parse" in joined:
            return FAKE_SHA
        if "check-runs" in joined:
            # `gate` green, `e2e` red: the release must proceed anyway.
            return (
                '{"check_runs":['
                '{"name":"gate","status":"completed","conclusion":"success"},'
                '{"name":"e2e","status":"completed","conclusion":"failure"}]}'
            )
        if "gh pr list" in joined:
            return "[]"
        if "gh label list" in joined:
            return '[{"name":"release-blocker"}]'
        if "describe --tags" in joined:
            return "v0.24.1"
        if "gh api" in joined:
            return "2026-09-17T00:00:00Z"
        return ""

    monkeypatch.setattr(release, "_check_output", fake_check_output)
    return calls


@pytest.fixture
def dry_run(no_network, monkeypatch):
    """A complete `--dry-run` pass over this repo with nothing shelling out.

    Returns (exit_code, runner, attempted_commands); `runner.planned` is every
    write the run would have performed.
    """
    monkeypatch.setattr(release, "read_pyproject_version", lambda repo: "0.24.2")
    monkeypatch.setattr(release, "check_changelog", lambda repo, v: None)
    monkeypatch.setattr(release, "release_notes_for", lambda repo, v: "- A release script.\n")

    def _go(argv=("0.24.2",)):
        code, runner = release.run_release(release.parse_args(list(argv)))
        return code, runner, no_network

    return _go


@pytest.fixture
def dry_run_commands(dry_run):
    _code, runner, _calls = dry_run()
    return runner.planned


# --------------------------------------------------------------------------
# version / changelog validation
# --------------------------------------------------------------------------


class TestReadVersion:
    def test_reads_the_project_version(self, repo):
        assert release.read_pyproject_version(repo) == "0.24.2"

    def test_missing_pyproject_is_an_error(self, tmp_path):
        with pytest.raises(release.ReleaseError, match="pyproject.toml"):
            release.read_pyproject_version(tmp_path)


class TestValidateVersionMatches:
    def test_matching_version_passes(self, repo):
        release.check_version_matches(repo, "0.24.2")  # no raise

    def test_mismatched_version_names_both(self, repo):
        with pytest.raises(release.ReleaseError) as excinfo:
            release.check_version_matches(repo, "0.25.0")
        message = str(excinfo.value)
        assert "0.24.2" in message and "0.25.0" in message

    def test_a_v_prefix_is_rejected_not_silently_stripped(self):
        with pytest.raises(release.ReleaseError, match="X.Y.Z"):
            release.normalize_version("v0.24.2")

    def test_non_semver_is_rejected(self):
        with pytest.raises(release.ReleaseError, match="X.Y.Z"):
            release.normalize_version("0.24")

    def test_plain_semver_is_accepted(self):
        assert release.normalize_version("0.24.2") == "0.24.2"


class TestChangelogValidation:
    def test_a_dated_section_with_content_passes(self, repo):
        release.check_changelog(repo, "0.24.2")  # no raise

    def test_missing_section_is_an_error(self, repo):
        with pytest.raises(release.ReleaseError, match=r"0\.25\.0"):
            release.check_changelog(repo, "0.25.0")

    def test_section_dated_other_than_today_is_an_error(self, repo):
        (repo / "CHANGELOG.md").write_text(GOOD_CHANGELOG.format(today="2020-01-01"))
        with pytest.raises(release.ReleaseError, match="2020-01-01"):
            release.check_changelog(repo, "0.24.2")

    def test_undated_section_is_an_error(self, repo):
        (repo / "CHANGELOG.md").write_text("# Changelog\n\n## [0.24.2]\n\n### Added\n\n- Thing.\n")
        with pytest.raises(release.ReleaseError, match="YYYY-MM-DD"):
            release.check_changelog(repo, "0.24.2")

    def test_empty_section_is_an_error(self, repo):
        (repo / "CHANGELOG.md").write_text(
            f"# Changelog\n\n## [0.24.2] - {date.today().isoformat()}\n\n"
            "## [0.24.1] - 2026-09-17\n\n- Older.\n"
        )
        with pytest.raises(release.ReleaseError, match="no content"):
            release.check_changelog(repo, "0.24.2")

    def test_unreleased_below_the_section_is_an_error(self, repo):
        """`[Unreleased]` must be empty or absent: entries under it below the
        released section are changes that would silently miss the release."""
        (repo / "CHANGELOG.md").write_text(
            f"# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Not shipped yet.\n\n"
            f"## [0.24.2] - {date.today().isoformat()}\n\n- Thing.\n"
        )
        with pytest.raises(release.ReleaseError, match="Unreleased"):
            release.check_changelog(repo, "0.24.2")

    def test_absent_unreleased_is_fine(self, repo):
        (repo / "CHANGELOG.md").write_text(
            f"# Changelog\n\n## [0.24.2] - {date.today().isoformat()}\n\n- Thing.\n"
        )
        release.check_changelog(repo, "0.24.2")  # no raise


# --------------------------------------------------------------------------
# notes extraction
# --------------------------------------------------------------------------


class TestExtractNotes:
    def test_takes_the_section_body_only(self, repo):
        notes = release.release_notes_for(repo, "0.24.2")
        assert "- A release script." in notes
        assert "0.24.1" not in notes
        assert "Unreleased" not in notes

    def test_does_not_include_the_heading_itself(self, repo):
        notes = release.release_notes_for(repo, "0.24.2")
        assert not notes.lstrip().startswith("## [0.24.2]")

    def test_last_section_in_the_file_still_extracts(self, repo):
        (repo / "CHANGELOG.md").write_text(
            f"# Changelog\n\n## [0.24.2] - {date.today().isoformat()}\n\n- Only one.\n"
        )
        assert "- Only one." in release.release_notes_for(repo, "0.24.2")

    def test_missing_section_is_an_error(self, repo):
        with pytest.raises(release.ReleaseError):
            release.release_notes_for(repo, "9.9.9")


class TestContributorsLine:
    def test_credits_outside_authors_sorted_and_deduped(self):
        line = release.contributors_line(["zoe", "amy", "zoe"])
        assert line == "Thanks to @amy, @zoe for their contributions."

    def test_maintainer_and_bots_are_excluded(self):
        assert release.contributors_line(["markramm", "dependabot[bot]"]) is None

    def test_no_outside_authors_yields_no_line(self):
        assert release.contributors_line([]) is None

    def test_one_author_reads_naturally(self):
        assert release.contributors_line(["amy"]) == ("Thanks to @amy for their contributions.")

    def test_notes_with_contributors_appends_the_line(self, repo):
        notes = release.compose_notes(repo, "0.24.2", ["amy"])
        assert notes.rstrip().endswith("Thanks to @amy for their contributions.")
        assert "- A release script." in notes

    def test_notes_without_contributors_are_the_section_alone(self, repo):
        notes = release.compose_notes(repo, "0.24.2", [])
        assert "Thanks to" not in notes


# --------------------------------------------------------------------------
# CI status decision, from mocked `gh run list` JSON
# --------------------------------------------------------------------------


def _run(status, conclusion, name="gate"):
    return {"status": status, "conclusion": conclusion, "name": name}


class TestCiDecision:
    """The verdict is over NAMED checks, not "everything on the SHA".

    `gate` is the required check (ADR-0032 §3a); `e2e` runs on pushes to main
    and is deliberately advisory -- it is not in `gate`'s needs, and a red e2e
    must not block a tag. Gating on every check run would make it block one.
    """

    def test_the_required_check_passing_passes(self):
        assert release.ci_decision([_run("completed", "success")]) == release.CI_PASSED

    def test_the_required_check_failing_fails(self):
        assert release.ci_decision([_run("completed", "failure")]) == release.CI_FAILED

    def test_in_progress_required_check_is_pending(self):
        assert release.ci_decision([_run("in_progress", None)]) == release.CI_PENDING

    def test_queued_required_check_is_pending(self):
        assert release.ci_decision([_run("queued", None)]) == release.CI_PENDING

    def test_no_checks_at_all_is_missing(self):
        assert release.ci_decision([]) == release.CI_MISSING

    def test_the_required_check_absent_is_missing(self):
        """Other checks ran but `gate` did not: that is not a green light."""
        assert release.ci_decision([_run("completed", "success", "smoke")]) == release.CI_MISSING

    def test_cancelled_is_a_failure_not_a_pass(self):
        assert release.ci_decision([_run("completed", "cancelled")]) == release.CI_FAILED

    def test_timed_out_is_a_failure(self):
        assert release.ci_decision([_run("completed", "timed_out")]) == release.CI_FAILED

    def test_skipped_required_check_passes(self):
        """ADR-0032: a skipped job is the classifier saying "nothing to test
        here", and `gate` itself reports success. A skipped check is a pass."""
        assert release.ci_decision([_run("completed", "skipped")]) == release.CI_PASSED

    def test_an_advisory_red_check_does_not_block(self):
        """The coupling that matters: `e2e` runs on pushes to main, is not in
        `gate`'s needs, and must never block a tag."""
        checks = [_run("completed", "success", "gate"), _run("completed", "failure", "e2e")]
        assert release.ci_decision(checks) == release.CI_PASSED

    def test_an_advisory_pending_check_does_not_hold_the_release(self):
        checks = [_run("completed", "success", "gate"), _run("in_progress", None, "e2e")]
        assert release.ci_decision(checks) == release.CI_PASSED

    def test_several_required_checks_all_must_pass(self):
        checks = [_run("completed", "success", "gate"), _run("completed", "failure", "kb")]
        assert release.ci_decision(checks, required=("gate", "kb")) == release.CI_FAILED

    def test_several_required_checks_pending_beats_passed(self):
        checks = [_run("completed", "success", "gate"), _run("queued", None, "kb")]
        assert release.ci_decision(checks, required=("gate", "kb")) == release.CI_PENDING

    def test_matrix_legs_match_by_prefix(self):
        """`test` reports as `test (3.12)` on a matrix and as `test` when the
        matrix is skipped -- requiring `test` must match both."""
        checks = [_run("completed", "success", "test (3.12)")]
        assert release.ci_decision(checks, required=("test",)) == release.CI_PASSED

    def test_the_default_required_check_is_gate(self):
        assert release.DEFAULT_REQUIRED_CHECKS == ("gate",)

    def test_require_check_is_configurable_on_the_command_line(self):
        args = release.parse_args(["0.24.2", "--require-check", "gate", "--require-check", "kb"])
        assert args.require_check == ["gate", "kb"]

    def test_require_check_defaults_to_gate(self):
        assert release.parse_args(["0.24.2"]).require_check == ["gate"]

    def test_e2e_is_never_required_by_default(self):
        assert "e2e" not in release.DEFAULT_REQUIRED_CHECKS
        assert "e2e" not in _string_literals(release)

    def test_never_dispatches_a_run(self):
        """A run this script started is not the run the merge gate saw, so it
        must never be able to start one: no `gh workflow run` argument anywhere."""
        literals = _string_literals(release)
        assert "workflow" not in literals
        assert not [s for s in literals if "workflow run" in s]

    def test_a_commit_github_has_never_seen_says_so_in_english(self, monkeypatch):
        """Found running it by hand: the likeliest real failure is a commit
        that was never pushed, and `gh` answers HTTP 422 'No commit found'.
        That must become the CI_MISSING advice, not a raw API error."""

        def explode(cmd, **kwargs):
            raise release.ReleaseError(
                "command failed (1): gh api repos/markramm/pyrite/commits/deadbeef/check-runs\n"
                '{"message":"No commit found for SHA: deadbeef","status":"422"}'
            )

        monkeypatch.setattr(release, "_check_output", explode)
        assert release._checks_for("deadbeef") == []

    def test_other_gh_errors_still_surface(self, monkeypatch):
        """Only 'no commit' is translated: a network or auth failure must not
        be mistaken for 'CI has not run yet'."""

        def explode(cmd, **kwargs):
            raise release.ReleaseError("command failed (1): gh api ...\nHTTP 401 Bad credentials")

        monkeypatch.setattr(release, "_check_output", explode)
        with pytest.raises(release.ReleaseError, match="401"):
            release._checks_for("deadbeef")


# --------------------------------------------------------------------------
# step ordering: no irreversible step before a check
# --------------------------------------------------------------------------


class TestStepOrdering:
    def test_every_step_is_named_and_classified(self):
        for step in release.STEPS:
            assert step.name
            assert isinstance(step.irreversible, bool)
            assert callable(step.run)

    def test_no_irreversible_step_precedes_a_check(self):
        """The whole point of the script: every check runs in front of the
        first thing that cannot be undone."""
        names = [s.name for s in release.STEPS]
        first_irreversible = next(i for i, s in enumerate(release.STEPS) if s.irreversible)
        last_check = max(i for i, s in enumerate(release.STEPS) if not s.irreversible)
        assert first_irreversible > last_check, (
            f"a check runs after the first irreversible step: {names}"
        )

    def test_the_documented_order_of_steps(self):
        assert [s.key for s in release.STEPS] == [
            "preconditions",
            "ci",
            "release_layer",
            "publish",
            "post_release",
        ]

    def test_only_publish_and_post_release_are_irreversible(self):
        irreversible = {s.key for s in release.STEPS if s.irreversible}
        assert irreversible == {"publish", "post_release"}


# --------------------------------------------------------------------------
# safety rules
# --------------------------------------------------------------------------


def _string_literals(module) -> list[str]:
    """Every string literal in the module that is not a docstring.

    The dangerous flags appear in this module's prose (its whole point is that
    v0.24.1 was pushed with --no-verify), so a substring scan of the source
    would be a test of the documentation. Command arguments are string
    literals; docstrings are not arguments.
    """
    import ast

    tree = ast.parse(Path(module.__file__).read_text())
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value not in docstrings
    ]


class TestSafety:
    def test_no_command_argument_is_no_verify(self):
        assert not [s for s in _string_literals(release) if "--no-verify" in s]

    def test_no_command_argument_force_pushes(self):
        dangerous = ("--force", "force-with-lease", "-f")
        literals = _string_literals(release)
        assert not [s for s in literals if s in dangerous or "--force" in s]

    def test_no_command_argument_deletes_a_ref(self):
        literals = _string_literals(release)
        assert not [s for s in literals if "--delete" in s]

    def test_the_only_push_refspecs_are_forward(self, dry_run_commands):
        """As actually composed in a dry run: `<sha>:refs/heads/main` and a tag
        name. A refspec starting with `:` deletes the remote ref; one starting
        with `+` forces. Neither may ever be built."""
        for cmd in dry_run_commands:
            if "push" not in cmd:
                continue
            for arg in cmd[cmd.index("push") + 1 :]:
                assert not arg.startswith(":"), f"deleting refspec: {cmd}"
                assert not arg.startswith("+"), f"forcing refspec: {cmd}"

    def test_dry_run_is_the_default(self):
        args = release.parse_args(["0.24.2"])
        assert args.execute is False

    def test_execute_flag_turns_it_off(self):
        args = release.parse_args(["0.24.2", "--execute"])
        assert args.execute is True

    def test_dry_run_flag_is_accepted_and_redundant(self):
        args = release.parse_args(["0.24.2", "--dry-run"])
        assert args.execute is False

    def test_dry_run_and_execute_together_is_refused(self, capsys):
        with pytest.raises(SystemExit):
            release.parse_args(["0.24.2", "--execute", "--dry-run"])

    def test_gh_writes_are_never_run_in_dry_run(self):
        """`gh release create` and `gh label create` are writes: in dry-run
        they are printed, never executed."""
        runner = release.Runner(execute=False)
        printed = runner.run_write(["gh", "release", "create", "v0.24.2"])
        assert printed is None  # nothing ran

    def test_a_write_in_execute_mode_calls_through(self, monkeypatch):
        calls = []
        monkeypatch.setattr(release, "_check_output", lambda cmd, **kw: calls.append(cmd) or "")
        runner = release.Runner(execute=True)
        runner.run_write(["gh", "release", "create", "v0.24.2"])
        assert calls == [["gh", "release", "create", "v0.24.2"]]

    def test_dirty_checkout_is_refused(self, monkeypatch):
        monkeypatch.setattr(release, "git_status_porcelain", lambda repo: " M foo.py")
        with pytest.raises(release.ReleaseError, match="dirty|uncommitted"):
            release.check_clean_checkout(REPO)

    def test_wrong_branch_is_refused(self, monkeypatch):
        monkeypatch.setattr(release, "git_status_porcelain", lambda repo: "")
        monkeypatch.setattr(release, "current_branch", lambda repo: "feature/x")
        with pytest.raises(release.ReleaseError, match="dev"):
            release.check_clean_checkout(REPO)

    def test_behind_origin_dev_is_refused(self, monkeypatch):
        monkeypatch.setattr(release, "git_status_porcelain", lambda repo: "")
        monkeypatch.setattr(release, "current_branch", lambda repo: "dev")
        monkeypatch.setattr(
            release, "rev_parse", lambda repo, ref: "aaa" if ref == "HEAD" else "bbb"
        )
        with pytest.raises(release.ReleaseError, match="origin/dev"):
            release.check_clean_checkout(REPO)

    def test_clean_dev_at_origin_dev_passes(self, monkeypatch):
        monkeypatch.setattr(release, "git_status_porcelain", lambda repo: "")
        monkeypatch.setattr(release, "current_branch", lambda repo: "dev")
        monkeypatch.setattr(release, "rev_parse", lambda repo, ref: "aaa")
        assert release.check_clean_checkout(REPO) == "aaa"


class TestReleaseBlockers:
    def test_an_open_blocker_pr_refuses(self):
        with pytest.raises(release.ReleaseError, match="#7"):
            release.check_no_release_blockers([{"number": 7, "title": "the index is corrupt"}])

    def test_no_blockers_passes(self):
        release.check_no_release_blockers([])  # no raise


# --------------------------------------------------------------------------
# --dry-run over this repo, with every subprocess call monkeypatched
# --------------------------------------------------------------------------


class TestDryRunOverThisRepo:
    def test_dry_run_exits_zero(self, dry_run):
        code, _runner, _calls = dry_run()
        assert code == 0

    def test_dry_run_shells_out_only_to_reads(self, dry_run):
        """Every subprocess the dry run attempted must be a read. A write that
        slipped past the Runner would show up here."""
        _code, _runner, calls = dry_run()
        joined = " ".join(" ".join(c) for c in calls)
        for write in ("push", " tag ", "release create", "label create", "uv venv", "uv pip"):
            assert write not in joined, f"dry run ran a write: {write!r} in {joined}"

    def test_gh_release_create_names_the_repo_explicitly(self, dry_run_commands):
        """`gh` infers the repo from the cwd, which is not necessarily the repo
        being released. A release cut against the wrong repo is not undoable."""
        create = [c for c in dry_run_commands if c[:3] == ["gh", "release", "create"]]
        assert create, "no release create was planned"
        for cmd in create:
            assert "--repo" in cmd
            assert cmd[cmd.index("--repo") + 1] == f"{release.MAINTAINER}/pyrite"

    def test_dry_run_planned_every_irreversible_command(self, dry_run_commands):
        planned = [" ".join(c) for c in dry_run_commands]
        assert any(f"push origin {FAKE_SHA}:refs/heads/main" in p for p in planned)
        assert any("tag -a v0.24.2" in p for p in planned)
        assert any("push origin v0.24.2" in p for p in planned)
        assert any("gh release create v0.24.2" in p for p in planned)

    def test_dry_run_prints_every_irreversible_command(self, dry_run, capsys):
        dry_run()
        out = capsys.readouterr().out
        assert f"push origin {FAKE_SHA}:refs/heads/main" in out
        assert "tag -a v0.24.2" in out
        assert "push origin v0.24.2" in out
        assert "gh release create v0.24.2" in out
        assert "WOULD RUN" in out

    def test_dry_run_prints_the_install_check_it_skipped(self, dry_run, capsys):
        """Step c is minutes of network; a dry run prints it and says how to
        rehearse it for real."""
        dry_run()
        out = capsys.readouterr().out
        assert "uv pip install" in out
        assert "--install-check" in out

    def test_printed_commands_are_copy_pasteable(self, dry_run, capsys):
        """Found running it by hand: an argument with spaces printed bare, so
        `gh label create ... --description Must not ship in the next release`
        could not be pasted into a shell. The maintainer pastes these."""
        import shlex

        dry_run()
        for line in capsys.readouterr().out.splitlines():
            for prefix in ("WOULD RUN: ", "RUN: "):
                if prefix in line:
                    rendered = line.split(prefix, 1)[1]
                    # every multi-word argument must be quoted: re-splitting the
                    # printed line must not invent extra arguments
                    assert shlex.split(rendered), rendered

    def test_an_argument_with_spaces_is_quoted_when_printed(self, capsys):
        runner = release.Runner(execute=False)
        runner.run_write(["gh", "label", "create", "x", "--description", "two words"])
        assert "'two words'" in capsys.readouterr().out

    def test_dry_run_says_it_is_a_dry_run(self, dry_run, capsys):
        dry_run()
        out = capsys.readouterr().out.lower()
        assert "dry run" in out
        assert "--execute" in out

    def test_a_failing_precondition_stops_before_later_steps(self, dry_run, monkeypatch, capsys):
        monkeypatch.setattr(release, "read_pyproject_version", lambda repo: "0.24.1")
        monkeypatch.setattr(
            release,
            "check_version_matches",
            lambda repo, v: (_ for _ in ()).throw(release.ReleaseError("version mismatch")),
        )
        code, runner, _calls = dry_run()
        assert code != 0
        assert runner.planned == [], "a write was planned after a failed check"
        captured = capsys.readouterr()
        assert "gh release create" not in captured.out

    def test_the_failure_reads_in_order_when_piped(self, tmp_path):
        """Found running it by hand: piped, stdout block-buffers while stderr
        does not, so `FAIL at preconditions` printed ABOVE the header and the
        step it failed in -- unreadable in a log or a CI transcript.

        Runs the real script as a subprocess with both streams on one pipe.
        `--repo` points at an empty tmp dir, so the very first check (git
        status) fails there: no network, no git writes, nothing reached.
        """
        import subprocess

        proc = subprocess.run(
            f'"{sys.executable}" "{REPO / "scripts" / "release.py"}" 0.0.1 '
            f'--repo "{tmp_path}" 2>&1',
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        out = proc.stdout
        assert proc.returncode != 0
        assert "FAIL at preconditions" in out
        assert out.index("pyrite release 0.0.1") < out.index("FAIL at")
        assert out.index("a. preconditions") < out.index("FAIL at")


# --------------------------------------------------------------------------
# the tutorial runner must be targetable at the temp venv (step c)
# --------------------------------------------------------------------------


class TestTutorialVenvHook:
    def test_run_tutorial_sh_honours_pyrite_tutorial_venv(self):
        script = (REPO / "scripts" / "run_tutorial.sh").read_text()
        assert "PYRITE_TUTORIAL_VENV" in script

    def test_release_script_targets_the_temp_venv_via_that_var(self):
        source = Path(release.__file__).read_text()
        assert "PYRITE_TUTORIAL_VENV" in source
