# Release & Deploy Runbook

Procedural reference for the `dev → main` release path and the deploy script. SKILL.md keeps the daily-development rules (branches, committing); this file holds the runbook steps that only fire when shipping.

> **Maintainer-only.** Cutting releases and running the deploy script need push
> rights to `main` and the gitignored `pyrite_deployments/` directory, which
> holds the maintainer's site configs. Contributors never need this file: open a
> PR against `dev` (see CONTRIBUTING.md).

## Releasing (dev → main)

Only merge `dev` → `main` when the user explicitly asks to release.

**The rule: the commit that gets tagged is a commit CI already passed.** All
release edits happen on `dev`; `main` only ever fast-forwards. Never commit on
`main` (a version bump there is an untested commit, and it makes `main` diverge
from `dev` so the next release needs a real merge).

```bash
# --- on dev -----------------------------------------------------------------
# 1. Release edits, in one commit:
#    - pyproject.toml `version` (the ONLY place it is written;
#      pyrite.__version__ reads it, tests/test_version_consistency.py checks it)
#    - CHANGELOG.md: date the section being released, `## [X.Y.Z] - YYYY-MM-DD`
#    - SECURITY.md supported-versions table, if the minor changed
git commit -m "release: prepare vX.Y.Z" -- pyproject.toml CHANGELOG.md
git push origin dev          # pre-push runs the full suite (~8 min)

# 2. Wait for CI on THAT commit. `test (3.12)` is the required check on main.
gh run list --branch dev --limit 1
SHA=$(git rev-parse dev)

# --- fast-forward main, tag, release ----------------------------------------
# 3. Fast-forward only. If this refuses, main has commits dev lacks: stop and
#    find out why (a hotfix that was never merged back?) before going further.
git checkout main && git pull --ff-only
git merge --ff-only "$SHA"
git tag -a vX.Y.Z -m "vX.Y.Z: one-line summary" "$SHA"
git push origin main && git push origin vX.Y.Z

# 4. GitHub release, notes taken from the CHANGELOG section
#    (does NOT publish to PyPI -- see note below)
gh release create vX.Y.Z --title "vX.Y.Z" --notes-file <(sed -n '/^## \[X.Y.Z\]/,/^## \[/p' CHANGELOG.md | sed '$d')

# 5. Verify what users will actually get, in a throwaway venv
python -m venv /tmp/relcheck && /tmp/relcheck/bin/pip install -q \
  "pyrite[all] @ git+https://github.com/markramm/pyrite@vX.Y.Z"
/tmp/relcheck/bin/python -c "import pyrite; print(pyrite.__version__)"   # X.Y.Z

# --- back on dev ------------------------------------------------------------
# 6. Open the next cycle: add an empty `## [Unreleased]` section at the top of
#    CHANGELOG.md so new entries stop landing in a version that is already cut.
git checkout dev
```

Version numbers follow the roadmap, not the calendar: a minor (0.25) names a
milestone with a definition of done. Do not tag it until that is met; ship
fixes as patch releases of the current minor meanwhile.

**PyPI**: not reachable. The `pyrite` name is held by a locked pre-2FA account (ADR-0025, amended 2026-09-17), so `publish.yml` is `workflow_dispatch`-only and a GitHub release publishes nothing. Install path is `pip install git+https://github.com/markramm/pyrite@<tag>`.

## Deploying

Use the deployment script at `pyrite_deployments/deploy.sh` (gitignored, local only):

```bash
# Check all sites
./pyrite_deployments/deploy.sh status

# Deploy latest dev to demo.pyrite.wiki
./pyrite_deployments/deploy.sh demo

# Deploy cascade (code only — fast, no re-index)
./pyrite_deployments/deploy.sh cascade

# Deploy cascade with full re-seed (re-copy KB data, rebuild index, re-export, re-render)
./pyrite_deployments/deploy.sh cascade --reseed

# Deploy specific tag to pyrite.ink
./pyrite_deployments/deploy.sh ink v0.21.0
```

**When to use `--reseed`:** when KB content changed (new events, fixed bodies), or when the export/render code changed (new fields in site cache, new source data in timeline.json).

## Hotfixes

For urgent fixes to a release:

Prefer a normal patch release (above): if `dev` is releasable, fast-forward it.
Only when `dev` carries work that must not ship yet:

1. Branch `hotfix/vX.Y.Z` from the release tag, cherry-pick the fix from `dev`,
   bump the patch version and CHANGELOG there, push, and wait for CI.
2. Fast-forward `main` to the hotfix branch, tag, release, deploy.
3. Merge `main` back into `dev` immediately, so `main` is an ancestor of `dev`
   again and the next release can fast-forward.

## Site mapping (which branch lands where)

| Site | Source | Trigger |
|------|--------|---------|
| `demo.pyrite.wiki` | `dev` HEAD | Auto on CI pass |
| `capturecascade.org` | `main` tag | Manual via `deploy.sh cascade` |
| `pyrite.ink` | `main` tag | Manual via `deploy.sh ink <tag>` |
| PyPI | — | Unreachable (locked account); `publish.yml` is manual-only |
