"""The commit/push/CI split is load-bearing, so it is pinned by tests.

See kb/backlog/fast-commit-hooks-full-suite-at-pre-push-ci-is-the-gate.md.

Commit-stage hooks stash every unstaged edit in the working tree while they
run. With several sessions sharing one tree, a multi-minute hook makes other
sessions' edits vanish for minutes and lets one session's untracked RED test
block everyone's commits. So: nothing slow at the commit stage, the full
suite at pre-push, CI as the authority.
"""

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def precommit() -> dict:
    return yaml.safe_load((REPO / ".pre-commit-config.yaml").read_text())


@pytest.fixture(scope="module")
def ci() -> dict:
    return yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text())


@pytest.fixture(scope="module")
def pyproject() -> dict:
    import tomllib

    return tomllib.loads((REPO / "pyproject.toml").read_text())


def _hooks(config: dict) -> list[dict]:
    return [hook for repo in config["repos"] for hook in repo["hooks"]]


def _stages(hook: dict, config: dict) -> set[str]:
    # A hook with no `stages` runs at every installed stage.
    return set(hook.get("stages") or config.get("default_stages") or ["pre-commit"])


def _local_hooks(config: dict) -> list[dict]:
    return [h for repo in config["repos"] if repo["repo"] == "local" for h in repo["hooks"]]


class TestPreCommitConfig:
    def test_no_commit_stage_hook_runs_pytest(self, precommit):
        offenders = [
            hook["id"]
            for hook in _hooks(precommit)
            if "pytest" in str(hook.get("entry", "")) and "pre-commit" in _stages(hook, precommit)
        ]
        assert offenders == [], f"pytest must not run at the commit stage: {offenders}"

    def test_full_suite_runs_at_pre_push(self, precommit):
        pushed = [
            hook
            for hook in _hooks(precommit)
            if "pytest" in str(hook.get("entry", "")) and _stages(hook, precommit) == {"pre-push"}
        ]
        assert len(pushed) == 1, "expected exactly one pre-push pytest hook"

    def test_pre_push_suite_is_scoped_to_code_changes(self, precommit):
        (hook,) = [h for h in _hooks(precommit) if "pytest" in str(h.get("entry", ""))]
        assert not hook.get("always_run"), "always_run defeats the docs-only skip"
        assert hook.get("files"), "pre-push pytest needs a `files:` filter"

    def test_local_hooks_do_not_discard_output(self, precommit):
        offenders = [h["id"] for h in _local_hooks(precommit) if "/dev/null" in h["entry"]]
        assert offenders == [], f"hooks must show why they failed: {offenders}"

    def test_local_hooks_do_not_require_an_activated_venv(self, precommit):
        offenders = [h["id"] for h in _local_hooks(precommit) if "activate" in h["entry"]]
        assert offenders == [], f"`source .venv/bin/activate` is not portable: {offenders}"

    def test_all_three_hook_types_install_by_default(self, precommit):
        # Without this, plain `pre-commit install` skips commit-msg and pre-push,
        # and the fix-commit-has-tests rule silently never runs for new clones.
        assert set(precommit.get("default_install_hook_types", [])) >= {
            "pre-commit",
            "commit-msg",
            "pre-push",
        }

    def test_kb_schema_validation_stays_at_commit_stage(self, precommit):
        (hook,) = [h for h in _hooks(precommit) if h["id"] == "pyrite-schema-validate"]
        assert "pre-commit" in _stages(hook, precommit)


class TestCIWorkflow:
    def test_superseded_runs_are_cancelled(self, ci):
        assert ci["concurrency"]["cancel-in-progress"] is True

    def test_ci_runs_the_checks_that_local_hooks_run(self, ci):
        # Outside contributors' PRs never run local hooks; CI has to.
        steps = "\n".join(
            str(step.get("run", "")) for job in ci["jobs"].values() for step in job["steps"]
        )
        assert "check_import_cycles.py" in steps
        assert "pyrite schema validate" in steps

    def test_no_duplicate_full_suite_job(self, ci):
        assert "test-optional-deps" not in ci["jobs"]

    def test_matrix_is_one_interpreter_on_pull_requests_and_all_on_pushes(self, ci):
        # `test (3.12)` is the required check for PRs; dev and main pushes run
        # the whole matrix (ADR-0032 §3 value chain).
        matrix = str(ci["jobs"]["test"]["strategy"]["matrix"]["python-version"])
        assert "github.event_name == 'pull_request'" in matrix
        assert '["3.12"]' in matrix
        assert '["3.11", "3.12", "3.13"]' in matrix


class TestPrePushStage:
    def test_only_pytest_runs_at_pre_push(self, precommit):
        # `default_stages` does NOT apply to hooks whose upstream manifest sets
        # its own `stages` (the pre-commit-hooks fixers list pre-push). Left
        # implicit, end-of-file-fixer ran over the whole dev..main range on the
        # v0.24.1 release push, rewrote two old KB files, and aborted the push
        # of a CI-verified commit. Every non-pytest hook must pin its stages.
        offenders = [
            hook["id"]
            for hook in _hooks(precommit)
            if "pytest" not in str(hook.get("entry", "")) and hook.get("stages") is None
        ]
        assert offenders == [], f"hooks relying on default_stages (pin `stages:`): {offenders}"


class TestParallelSuite:
    # Serial: tests/ alone took 7m41s locally and ~22 min in CI. Parallel:
    # tests/ + extensions/ in ~2-3 min. ADR-0032's up-to-date requirement is
    # only livable with the fast number, so both gates pin -n auto.
    def test_pre_push_runs_the_suite_in_parallel_including_extensions(self, precommit):
        (hook,) = [h for h in _hooks(precommit) if "pytest" in str(h.get("entry", ""))]
        assert "-n auto" in hook["entry"]
        assert "extensions/" in hook["entry"]

    def test_ci_runs_the_suite_in_parallel(self, ci):
        runs = [
            str(step.get("run", ""))
            for job in ci["jobs"].values()
            for step in job["steps"]
            if "pytest" in str(step.get("run", ""))
        ]
        assert runs, "no pytest step in CI"
        assert all("-n auto" in r for r in runs), runs


class TestCIInstall:
    def test_python_jobs_install_with_uv(self, ci):
        # pip spent 80-130 s per job resolving and building seven editable
        # installs even with a warm wheel cache; uv does the same in seconds.
        # It is also the install path the README documents (uv tool install).
        job = ci["jobs"]["test"]
        install = [s for s in job["steps"] if s.get("name") == "Install dependencies"]
        assert install, "no 'Install dependencies' step"
        run = str(install[0].get("run", ""))
        assert "uv pip install" in run, run
        assert "pip install -e" not in run.replace("uv pip install -e", ""), run
        assert any("setup-uv" in str(s.get("uses", "")) for s in job["steps"])


class TestPinnedTestRunner:
    """One pytest and xdist version for every venv and every CI leg (#128).

    CI resolved pytest 9.1.1 on 3.12 and 9.0.2 on 3.13 from an unbounded
    `pytest>=8.0.0`; every worktree venv got 9.1.1, the main checkout 9.0.2.
    #81's `@classmethod` fixtures passed the one-interpreter PR gate on
    whichever pytest resolved there and broke `dev` twice on 3.13 (fixed in
    #129). Pinning `==` makes the runner identical on every interpreter and
    every venv, and makes loosening the pin a visible diff instead of a
    silent `uv pip install` drift.
    """

    _PINNED = {"pytest", "pytest-cov", "pytest-xdist"}

    def _dev_extra(self, pyproject: dict) -> list[str]:
        return pyproject["project"]["optional-dependencies"]["dev"]

    def test_dev_extra_pins_the_test_runner_exactly(self, pyproject):
        specs = self._dev_extra(pyproject)
        pinned = {}
        for spec in specs:
            for name in self._PINNED:
                if spec == name or spec.startswith(name + "=="):
                    pinned[name] = spec

        missing = self._PINNED - set(pinned)
        assert not missing, f"not pinned at all in dev extras: {missing}"

        loose = [spec for spec in pinned.values() if "==" not in spec]
        assert not loose, f"pinned package without an exact '==' pin: {loose}"

    def test_no_other_version_operator_survives_for_pinned_packages(self, pyproject):
        # >=, <=, ~=, != on a pinned package would defeat the point silently.
        specs = self._dev_extra(pyproject)
        for spec in specs:
            for name in self._PINNED:
                if spec.split("=")[0].split(">")[0].split("<")[0].split("~")[0].strip() == name:
                    assert spec.count("==") == 1 and not any(
                        op in spec for op in (">=", "<=", "~=", "!=")
                    ), spec


class TestChangeClassifier:
    """Docs/KB-only pushes must not wait for the Python suite (ADR-0032 §2).

    A required check cannot simply be path-filtered out of the workflow --
    GitHub then reports it "pending" forever and the PR can never merge -- so
    the workflow always triggers, one job classifies the change, and the heavy
    jobs skip. A skipped job satisfies a required check.
    """

    def test_a_classifier_job_exists(self, ci):
        job = ci["jobs"]["changes"]
        assert any("paths-filter" in str(s.get("uses", "")) for s in job["steps"])
        assert set(job["outputs"]) >= {"backend", "web", "kb"}

    @pytest.mark.parametrize("name", ["test", "frontend"])
    def test_heavy_jobs_are_gated_on_the_classifier(self, ci, name):
        job = ci["jobs"][name]
        assert "changes" in job.get("needs", []), f"{name} must need: changes"
        assert "needs.changes.outputs" in str(job.get("if", "")), f"{name} has no if:"

    def test_release_branch_always_runs_everything(self, ci):
        # main only moves by fast-forward to a CI-verified SHA; never let a
        # docs-only classification on main skip the proof.
        for name in ("test", "frontend"):
            assert "refs/heads/main" in str(ci["jobs"][name]["if"])

    def test_kb_changes_get_their_own_fast_check(self, ci):
        job = ci["jobs"]["kb"]
        assert "needs.changes.outputs.kb" in str(job["if"])
        steps = "\n".join(str(s.get("run", "")) for s in job["steps"])
        assert "pyrite schema validate" in steps


class TestCoverageAndE2EPolicy:
    def test_matrix_jobs_do_not_collect_coverage(self, ci):
        # Coverage doubled the 3.12 test step (214 s vs ~90 s). It lives in its
        # own non-required job; the matrix is the fast gate.
        runs = "\n".join(str(s.get("run", "")) for s in ci["jobs"]["test"]["steps"])
        assert "--cov" not in runs

    def test_coverage_has_its_own_job_and_is_manual_for_now(self, ci):
        job = ci["jobs"]["coverage"]
        runs = "\n".join(str(s.get("run", "")) for s in job["steps"])
        assert "--cov=pyrite" in runs and "-n auto" in runs
        assert str(job["if"]).strip() == "github.event_name == 'workflow_dispatch'"

    def test_e2e_is_manual_only_until_deterministic(self, ci):
        # Non-deterministic today: a different set of specs fails every run,
        # so it carries no signal. Manual dispatch only; back on every push
        # when playwright-e2e-suite-non-deterministic-failures-... lands.
        cond = str(ci["jobs"]["e2e"]["if"]).strip()
        assert cond == "github.event_name == 'workflow_dispatch'", cond
        assert "workflow_dispatch" in ci[True] if True in ci else ci["on"]


class TestSessionSetupScript:
    def test_new_worktree_script_is_present_and_parses(self):
        import os
        import subprocess

        script = REPO / "scripts" / "new-worktree.sh"
        assert script.exists(), "ADR-0032 migration step 3: scripts/new-worktree.sh"
        assert os.access(script, os.X_OK), "must be executable"
        subprocess.run(["bash", "-n", str(script)], check=True)
        text = script.read_text()
        assert "git worktree add" in text and "pre-commit install" in text
        # The hook shim embeds the installing Python's path. Installing from a
        # worktree's venv breaks every checkout's hooks when that worktree is
        # removed; the script must install from the main checkout's venv.
        assert '"$repo_root/.venv/bin/pre-commit"' in text


class TestGateJob:
    """One required check that always reports (ADR-0032 §2).

    A skipped matrix job reports as `test`, not `test (3.12)`, so a docs-only
    PR whose classifier skipped the matrix could never satisfy a required
    `test (3.12)` and hung BLOCKED (PR #36, 2026-09-18). `gate` needs every
    job, runs `if: always()`, fails only on a real failure or cancellation,
    and is the only required check on dev and main.
    """

    def test_gate_needs_every_gating_job_and_always_runs(self, ci):
        job = ci["jobs"]["gate"]
        assert set(job["needs"]) >= {"changes", "kb", "test", "frontend"}
        assert str(job.get("if", "")).strip() == "always()"

    def test_gate_fails_on_failure_or_cancellation_only(self, ci):
        run = "\n".join(str(s.get("run", "")) for s in ci["jobs"]["gate"]["steps"])
        pattern = next(line for line in run.splitlines() if "grep" in line)
        assert "failure" in pattern and "cancelled" in pattern
        assert "skipped" not in pattern, "skipped must count as passing"


class TestJobPermissions:
    """Least privilege, stated (CodeQL actions/missing-workflow-permissions x8).

    Every job in ci.yml used to run with the repository's default GITHUB_TOKEN
    scope -- broader than any job here needs. A workflow-level `contents: read`
    covers checkout; a job gets its own `permissions:` block only when a step
    needs something more, so a future job that skips this is a silent
    escalation, not an oversight this suite would have caught.
    """

    def test_workflow_level_permissions_default_to_read_only(self, ci):
        assert ci["permissions"] == {"contents": "read"}

    def test_every_job_is_covered_by_a_permissions_block(self, ci):
        # Workflow-level `contents: read` covers a job with no block of its
        # own; a job that needs more must say so explicitly so the grant is
        # visible at the job, not just inherited silently. The classifier
        # job's dorny/paths-filter step needs to read PR metadata on
        # pull_request events; every other job's steps (checkout, setup-*,
        # pytest, npm, upload-artifact) work fine read-only.
        changes_job = ci["jobs"]["changes"]
        assert changes_job.get("permissions", {}).get("pull-requests") == "read", (
            "dorny/paths-filter needs pull-requests: read on pull_request events"
        )
        for name, job in ci["jobs"].items():
            if name == "changes":
                continue
            # No other job may claim more than the workflow-level default;
            # if one does, it must be a job-level block with a comment
            # justifying it (reviewed by hand, not by this test).
            assert job.get("permissions", {}).get("contents", "read") == "read", name

    def test_paths_filter_job_permissions_block_is_commented(self):
        # A grant with no reason attached is indistinguishable from a mistake
        # six months later. Require the comment live next to the block.
        text = (REPO / ".github" / "workflows" / "ci.yml").read_text()
        # Anchor on the step that USES paths-filter, not any prose mentioning
        # it (a comment above the permissions: block would otherwise match
        # first and cut the block out of `before`).
        idx = text.index("uses: dorny/paths-filter")
        before = text[:idx]
        changes_idx = before.rindex("\n  changes:")
        block = text[changes_idx:idx]
        assert "permissions:" in block
        assert "pull-requests: read" in block
        assert "#" in block, "the grant needs a one-line reason in a comment"


class TestSmokeLayer:
    """ADR-0032 §3a's "breadth" row: prove the assembled thing, not the units.

    The matrix proves the code on three interpreters. Nothing proved a real
    server process, a real client and the documented CLI worked together --
    and all three bugs the outside contributor found (PRs #3, #4, #5) lived in
    exactly that gap. The smoke layer closes it on the push to dev, where it
    costs minutes that no pull request has to wait for.
    """

    def test_e2e_marker_is_declared(self, pyproject):
        markers = pyproject["tool"]["pytest"]["ini_options"]["markers"]
        assert any(m.startswith("e2e:") for m in markers), markers

    def test_default_run_excludes_e2e(self, pyproject):
        # tests/e2e lives under testpaths, so without this every `pytest
        # tests/` -- including the pre-push hook and the PR matrix -- would
        # start server subprocesses and blow the ~3 min PR budget.
        addopts = pyproject["tool"]["pytest"]["ini_options"]["addopts"]
        assert "not e2e" in addopts, addopts

    def test_smoke_job_is_gated_on_dev_or_dispatch(self, ci):
        cond = str(ci["jobs"]["smoke"]["if"])
        assert "refs/heads/dev" in cond, cond
        assert "workflow_dispatch" in cond, cond
        assert "pull_request" not in cond, "smoke must never run on a PR"

    def test_smoke_job_needs_the_classifier(self, ci):
        assert "changes" in ci["jobs"]["smoke"]["needs"]

    def test_smoke_is_not_a_required_check(self, ci):
        # `gate` is the one required check. Adding smoke to its needs would
        # make a minutes-long job block every PR -- the opposite of the point.
        assert "smoke" not in ci["jobs"]["gate"]["needs"]

    def test_smoke_job_runs_the_e2e_marker_and_the_tutorial(self, ci):
        runs = "\n".join(str(s.get("run", "")) for s in ci["jobs"]["smoke"]["steps"])
        assert "-m e2e" in runs and "tests/e2e" in runs, runs
        assert "run_tutorial.sh" in runs, runs

    def test_smoke_keeps_each_file_on_one_worker(self, ci):
        # The server fixtures are module-scoped and xdist re-runs those per
        # worker. Under the default `load` distribution one file's tests scatter
        # across workers and each starts its own server: 46 s instead of 22 s.
        runs = "\n".join(str(s.get("run", "")) for s in ci["jobs"]["smoke"]["steps"])
        assert "--dist loadfile" in runs, runs

    def test_smoke_job_installs_the_full_surface_like_test(self, ci):
        runs = "\n".join(str(s.get("run", "")) for s in ci["jobs"]["smoke"]["steps"])
        assert "uv pip install" in runs, runs
        assert ".[all]" in runs, runs
        assert "extensions/*/" in runs, "extensions are separate distributions"

    def test_tutorial_runner_exists_and_parses(self):
        import os
        import subprocess

        script = REPO / "scripts" / "run_tutorial.sh"
        assert script.exists(), "docs-as-tests runner for docs/getting-started.md"
        assert os.access(script, os.X_OK), "must be executable"
        subprocess.run(["bash", "-n", str(script)], check=True)
