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
