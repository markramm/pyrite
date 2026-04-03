---
id: adr-0025
type: adr
title: "Release Workflow: Dev Branch, Tagged Releases, and Deployment Tiers"
adr_number: 25
status: accepted
deciders: ["markr"]
date: "2026-04-01"
tags: [process, releases, deployment, git, ci]
---

# ADR-0025: Release Workflow: Dev Branch, Tagged Releases, and Deployment Tiers

## Context

Pyrite has been developed on `main` with direct pushes. This worked during solo development but is now untenable:

- **Multiple live deployments** (demo.pyrite.wiki, capturecascade.org) pull from `main` HEAD.
- **External users** are installing from PyPI and GitHub. Breaking `main` breaks them.
- **Development velocity is high** — 20+ changes in a single session is common. Any of these could break a deployment.
- **The cascade Dockerfile** clones `pyrite.git` at build time with `--depth=1`, getting whatever is on `main`.
- **PyPI publishes** are triggered by GitHub releases but there's no systematic tagging (pyproject.toml says 0.20.0, git has only a v0.6.0 tag).

Full gitflow is unnecessary — there are only a handful of users and no formal QA process. But the minimum viable discipline is: don't deploy untested code to live sites.

## Decision

### Branching Model

**Two long-lived branches:**

- **`main`** — stable releases only. Every commit on `main` is a tagged release (or a merge preparing one). capturecascade.org and early adopters track this.
- **`dev`** — daily development. All feature work, bug fixes, and experiments land here. CI runs on every push. demo.pyrite.wiki tracks this (dogfooding).

**Short-lived feature branches** (optional): for large multi-day changes that would destabilize `dev`. Branch from `dev`, merge back to `dev`. Named `feature/<slug>` or `fix/<slug>`.

### Three Deployment Tiers

| Tier | Branch | Who | Stability | Updates |
|------|--------|-----|-----------|---------|
| **Development** | `dev` | demo.pyrite.wiki | Latest, may break | Auto-deploy on CI pass |
| **Stable** | `main` (tags) | capturecascade.org, early adopters | Tested, release-gated | Manual deploy of tagged release |
| **Published** | Tags → PyPI | `pip install pyrite` users | Formally released | GitHub release triggers PyPI publish |

### Release Process

1. Work accumulates on `dev` until a release is warranted.
2. CI must be green on `dev` — this is a hard gate for merge to `main`.
3. Merge `dev` → `main` (fast-forward or merge commit, no squash — preserve history).
4. Tag `main` with a semver tag: `v0.21.0`, `v0.21.1`, etc.
5. Bump `pyproject.toml` version on `dev` to the next dev version.
6. Create a GitHub release from the tag (triggers PyPI publish via existing workflow).
7. Deploy stable sites by updating their version reference and rebuilding.

### CI and Gating

**On push to `dev`:**
- Run full test suite (backend + frontend + extensions)
- Run linting (ruff)
- On pass: auto-deploy demo.pyrite.wiki (optional, can be triggered manually)

**Merge `dev` → `main` gated on:**
- All CI checks passing on `dev`
- Branch protection rule on `main`: require status checks to pass

**On push to `main`:**
- Run full test suite (confirmation)
- On tag: trigger PyPI publish

**GitHub branch protection on `main`:**
- Require status checks to pass before merging
- No force pushes
- No deletions

### Version Numbering

Continue from the current pyproject.toml version (0.20.0). Current release is **v0.21.0**.

- **Minor** (0.X.0): features, non-breaking changes, accumulated bug fixes.
- **Patch** (0.X.Y): urgent fixes to a release (cherry-pick to `main`, tag, release).
- **Major** (1.0.0): public announcement / API stability commitment. Not yet.

Dev versions use PEP 440 dev suffix: `0.22.0.dev0`.

### Deployment References

Deploy scripts and Dockerfiles reference specific tags, not branch HEAD:

```dockerfile
# Cascade and stable deployments pin to a release tag:
ARG PYRITE_VERSION=v0.21.0
RUN git clone --branch $PYRITE_VERSION --depth=1 https://github.com/markramm/pyrite.git /tmp/pyrite
```

```bash
# Demo tracks dev branch:
git checkout dev && git pull
```

### What This Does NOT Include

- **No PR reviews** — solo developer + AI agents, PRs add ceremony without value right now.
- **No release branches** — unnecessary at current scale. If a patch is needed, cherry-pick to `main` and tag.
- **No changelog generation** — keep it manual for now. Consider `git-cliff` later.

## Consequences

### Positive
- Live stable sites no longer break from untested development pushes
- Demo site dogfoods latest development for fast feedback
- Users and stable deployments can pin to a known-good version
- PyPI releases align with git tags
- Rollback is trivial: deploy the previous tag
- CI gating provides a quality floor for releases

### Negative
- Small overhead: merge `dev` → `main` when releasing
- Must remember to bump version after tagging
- Deploy scripts need the version arg updated for each upgrade

### Migration (completed 2026-04-01)

1. Tagged `main` as `v0.21.0` ✓
2. Created `dev` branch from `main` ✓
3. Updated cascade Dockerfile to pin `PYRITE_VERSION=v0.21.0` ✓
4. Updated demo `update.sh` to accept optional tag arg ✓
5. Set GitHub default branch to `dev` ✓
6. CI extended to run on both `main` and `dev` ✓
7. Bumped pyproject.toml on `dev` to `0.22.0.dev0` ✓
8. Branch protection on `main` — pending
9. Auto-deploy demo on dev CI pass — pending
