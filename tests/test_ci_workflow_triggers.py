"""`ci.yml` must gate a merge group, and must fail CLOSED when it cannot classify it.

GitHub's merge queue needs a `merge_group:` trigger before it can be switched
on: a queued PR waits on the required check (`gate`), and a workflow that does
not trigger on `merge_group` never produces one. See GitHub issue #273.

The hazard this module exists for is not "CI breaks loudly" -- it is `gate`
going GREEN on a merge group where every job skipped:

`changes` classifies the diff with `dorny/paths-filter`, which reads the PR's
changed-file list only for the events in its own `prEvents` list
(`pull_request`, `pull_request_target`, `pull_request_review`,
`pull_request_review_comment`). `merge_group` is NOT one of them (upstream
issue dorny/paths-filter#280), so on a merge group the action falls through to
`getChangedFilesFromGit(base, ref)` with `base` unset -- which resolves to
`github.context.payload.repository.default_branch` (`dev` here) and diffs the
`gh-readonly-queue/...` ref against it, over a checkout whose default
`fetch-depth: 1` does not contain that history. That path either errors or
yields an arbitrary classification.

Whatever it yields, the downstream failure is the same shape: every heavy job
is `if: needs.changes.outputs.<x> == 'true'`, a skipped job satisfies a
required check, and `gate` is `if: always()` failing only on
`failure|cancelled`. An all-false classification therefore skips the entire
matrix and reports the one required check GREEN having tested nothing -- which
is strictly worse than having no merge queue at all.

So `changes` must not depend on that action's merge_group behaviour. On
`merge_group` it reports EVERYTHING changed and runs the full matrix. Running
too much for a queued group is correct and cheap; running nothing and saying
so in green is not.
"""

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
CI_PATH = REPO / ".github" / "workflows" / "ci.yml"

# `on:` is the YAML 1.1 boolean `true`, so PyYAML parses the key as True, not
# the string "on". Every read of the trigger block goes through this.
ON = True


@pytest.fixture(scope="module")
def ci() -> dict:
    return yaml.safe_load(CI_PATH.read_text())


@pytest.fixture(scope="module")
def triggers(ci: dict) -> dict:
    block = ci.get(ON, ci.get("on"))
    assert isinstance(block, dict), f"unexpected `on:` block: {block!r}"
    return block


@pytest.fixture(scope="module")
def changes_job(ci: dict) -> dict:
    return ci["jobs"]["changes"]


class TestMergeGroupTrigger:
    """The trigger itself. Without it the merge queue cannot be enabled at all."""

    def test_ci_triggers_on_merge_group(self, triggers):
        assert "merge_group" in triggers, (
            "ci.yml must trigger on merge_group or GitHub's merge queue cannot be "
            f"enabled -- a queued PR waits forever for `gate`. Triggers: {sorted(map(str, triggers))}"
        )

    def test_existing_triggers_are_kept(self, triggers):
        # Adding merge_group must not cost the events the gate already runs on.
        assert {"push", "pull_request", "workflow_dispatch"} <= set(map(str, triggers))

    def test_push_and_pull_request_still_target_main_and_dev(self, triggers):
        for event in ("push", "pull_request"):
            assert set(triggers[event]["branches"]) == {"main", "dev"}, event


class TestGateIsReachableOnAMergeGroup:
    """`gate` is the one required check; the queue blocks until it reports."""

    def test_gate_has_no_event_condition_that_excludes_merge_group(self, ci):
        # `if: always()` and nothing else -- an event allowlist here would make
        # the required check never arrive for a queued group.
        assert str(ci["jobs"]["gate"].get("if", "")).strip() == "always()"

    def test_gate_still_needs_every_gating_job(self, ci):
        assert set(ci["jobs"]["gate"]["needs"]) >= {"changes", "kb", "test", "frontend"}

    @pytest.mark.parametrize("name", ["changes", "kb", "test", "frontend", "gate"])
    def test_no_gating_job_is_switched_off_for_merge_group(self, ci, name):
        # A job whose `if:` names merge_group only to exclude it would skip the
        # proof while still satisfying the required check.
        cond = str(ci["jobs"][name].get("if", ""))
        assert "!= 'merge_group'" not in cond.replace('"', "'"), cond


class TestChangesFailsClosedOnAMergeGroup:
    """The dangerous case: a classification of NOTHING would pass `gate` green.

    `dorny/paths-filter` has no merge_group support (upstream #280). Rather
    than depend on what it does there, the job must classify a merge group
    itself, as everything-changed.
    """

    def test_paths_filter_does_not_run_on_merge_group(self, changes_job):
        # The action's merge_group path is undefined-by-upstream; it must not
        # be the thing deciding whether the matrix runs for a queued commit.
        filter_steps = [s for s in changes_job["steps"] if "paths-filter" in str(s.get("uses", ""))]
        assert filter_steps, "the classifier still needs paths-filter for PR/push events"
        for step in filter_steps:
            cond = str(step.get("if", "")).replace('"', "'")
            assert "merge_group" in cond, (
                "the paths-filter step must be guarded so it does not run on "
                f"merge_group events (upstream dorny/paths-filter#280): if={cond!r}"
            )
            assert "!=" in cond, f"the guard must EXCLUDE merge_group, not require it: {cond!r}"

    def test_a_step_classifies_a_merge_group_as_everything_changed(self, changes_job):
        """Fail closed: when the paths cannot be determined, report everything."""
        merge_group_steps = [
            s
            for s in changes_job["steps"]
            if "merge_group" in str(s.get("if", "")).replace('"', "'")
            and "!=" not in str(s.get("if", ""))
        ]
        assert merge_group_steps, (
            "no step runs ON merge_group -- with paths-filter guarded off, every "
            "output would be empty, every heavy job would skip, and `gate` would "
            "report GREEN having tested nothing"
        )
        body = "\n".join(str(s.get("run", "")) for s in merge_group_steps)
        for name in ("backend", "web", "kb", "infra"):
            assert f"{name}=true" in body.replace(" ", ""), (
                f"the merge_group fallback must set {name}=true (everything changed); "
                f"anything else lets a queued group skip the matrix. Got:\n{body}"
            )

    @pytest.mark.parametrize("output", ["backend", "web", "kb", "infra"])
    def test_every_classifier_output_is_set_by_the_merge_group_step_too(self, changes_job, output):
        """An output only paths-filter sets is empty on a merge group -> skip -> green."""
        expr = str(changes_job["outputs"][output])
        ids = {
            part.split("steps.", 1)[1].split(".", 1)[0]
            for part in expr.split("||")
            if "steps." in part
        }
        step_ids = {s.get("id") for s in changes_job["steps"]}
        assert len(ids) >= 2, (
            f"output {output!r} reads from a single step ({expr!r}); on merge_group "
            "that step is guarded off and the output is empty, which reads as "
            "'not changed' and skips the job"
        )
        assert ids <= step_ids, f"output {output!r} references unknown step ids: {ids - step_ids}"

    def test_a_merge_group_runs_the_full_interpreter_matrix(self, ci):
        # The narrow one-interpreter leg is keyed on `pull_request`, so a
        # merge group falls to the full matrix. That is the right default for
        # the commit that actually lands: #133's bug passed on 3.12 and broke
        # dev on 3.13.
        matrix = str(ci["jobs"]["test"]["strategy"]["matrix"]["python-version"])
        assert "github.event_name == 'pull_request'" in matrix, matrix
        narrow, _, wide = matrix.partition("||")
        assert '["3.12"]' in narrow and '["3.11", "3.12", "3.13"]' in wide, matrix

    @pytest.mark.parametrize("job", ["kb", "test", "frontend"])
    def test_every_gated_job_runs_on_a_merge_group(self, ci, job):
        # Each reads `needs.changes.outputs.<x> == 'true'`, and the fallback
        # step sets all four to "true" -- so none of them skips on a queued
        # group. This is the assertion that "gate green on a skipped matrix"
        # cannot happen.
        cond = str(ci["jobs"][job]["if"])
        outputs = ci["jobs"]["changes"]["outputs"]
        referenced = [name for name in outputs if f"needs.changes.outputs.{name}" in cond]
        assert referenced, f"{job} is not gated on the classifier at all: {cond}"
        for name in referenced:
            assert "steps.all.outputs" in str(outputs[name]), (
                f"{job} gates on {name!r}, which has no merge_group fallback: {outputs[name]!r}"
            )

    def test_the_pr_only_fix_commit_check_stays_pr_only(self, ci):
        # It walks github.event.pull_request.base.sha, which does not exist on
        # a merge group; left ungated it would fail the matrix on every queued
        # commit. The PR gate already enforced the rule before queueing.
        step = next(
            s
            for s in ci["jobs"]["test"]["steps"]
            if "check_fix_commit_has_tests.py" in str(s.get("run", ""))
        )
        assert str(step["if"]).strip() == "github.event_name == 'pull_request'", step["if"]

    def test_outputs_do_not_silently_default_to_false(self, changes_job):
        # `x == 'true'` on an empty string is false -- a skip. The merge_group
        # branch must be reached by the expression, not fall off the end.
        for name, expr in changes_job["outputs"].items():
            assert "||" in str(expr), (
                f"output {name!r} has no fallback: {expr!r}. With paths-filter "
                "guarded off on merge_group this evaluates empty and the job skips."
            )


class TestPullRequestAndPushBehaviourIsUnchanged:
    """Regression guard: the merge_group work must not widen the PR gate."""

    def test_docs_only_pr_still_skips_the_backend_matrix(self, ci):
        # `test` remains gated on the classifier, so a docs-only PR (backend
        # false) still skips it. If this ever became unconditional, every
        # docs PR would pay for the matrix again.
        cond = str(ci["jobs"]["test"]["if"])
        assert "needs.changes.outputs.backend == 'true'" in cond, cond
        assert "always()" not in cond, cond

    def test_a_backend_pr_still_runs_the_matrix(self, ci):
        filters = yaml.safe_load(
            next(
                s["with"]["filters"]
                for s in ci["jobs"]["changes"]["steps"]
                if "filters" in s.get("with", {})
            )
        )
        assert "pyrite/**" in filters["backend"]

    def test_pr_matrix_is_still_one_interpreter(self, ci):
        matrix = str(ci["jobs"]["test"]["strategy"]["matrix"]["python-version"])
        assert "github.event_name == 'pull_request'" in matrix, matrix
        assert '["3.12"]' in matrix and '["3.11", "3.12", "3.13"]' in matrix

    def test_smoke_still_never_runs_on_a_pull_request(self, ci):
        assert "pull_request" not in str(ci["jobs"]["smoke"]["if"])


class TestNoNewDependencies:
    """Hard project rule: new deps need prior discussion on a ticket."""

    def test_classifier_uses_only_actions_already_in_the_workflow(self, ci):
        allowed = {
            "actions/checkout",
            "actions/setup-python",
            "actions/setup-node",
            "actions/cache",
            "actions/upload-artifact",
            "astral-sh/setup-uv",
            "dorny/paths-filter",
        }
        used = {
            str(step["uses"]).split("@", 1)[0]
            for job in ci["jobs"].values()
            for step in job["steps"]
            if step.get("uses")
        }
        assert used <= allowed, f"new action dependency introduced: {used - allowed}"


class TestWorkflowStillParses:
    def test_ci_yaml_is_valid(self, ci):
        assert ci["name"] == "CI"
        assert "gate" in ci["jobs"]
