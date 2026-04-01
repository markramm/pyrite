---
id: adr-0025
type: adr
title: "Release Workflow: Dev Branch and Tagged Releases"
adr_number: 25
status: accepted
deciders: ["markr"]
date: "2026-04-01"
tags: [process, releases, deployment, git]
---

# ADR-0025: Release Workflow: Dev Branch and Tagged Releases

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

- **`main`** — stable releases only. Every commit on `main` is a tagged release (or a merge preparing one). Deployments reference `main` tags.
- **`dev`** — daily development. All feature work, bug fixes, and experiments land here. CI runs on every push.

**Short-lived feature branches** (optional): for large multi-day changes that would destabilize `dev`. Branch from `dev`, merge back to `dev`. Named `feature/<slug>` or `fix/<slug>`.

### Release Process

1. Work accumulates on `dev` until a release is warranted.
2. Merge `dev` → `main` (fast-forward or merge commit, no squash — preserve history).
3. Tag `main` with a semver tag: `v0.21.0`, `v0.21.1`, etc.
4. Bump `pyproject.toml` version on `dev` to the next dev version.
5. Create a GitHub release from the tag (triggers PyPI publish via existing workflow).

### Version Numbering

Continue from the current pyproject.toml version (0.20.0). Next release is **v0.21.0**.

- **Minor** (0.X.0): features, non-breaking changes, accumulated bug fixes.
- **Patch** (0.X.Y): urgent fixes to a release (cherry-pick to `main`, tag, release).
- **Major** (1.0.0): public announcement / API stability commitment. Not yet.

Pre-release suffixes for testing: `v0.21.0-rc1`, `v0.21.0-alpha`.

### Deployment References

Deploy scripts and Dockerfiles reference specific tags, not branch HEAD:

```dockerfile
# Before (fragile):
RUN git clone --depth=1 https://github.com/markramm/pyrite.git /tmp/pyrite

# After (stable):
ARG PYRITE_VERSION=v0.21.0
RUN git clone --branch $PYRITE_VERSION --depth=1 https://github.com/markramm/pyrite.git /tmp/pyrite
```

The `update.sh` scripts pull the configured tag and rebuild. Upgrading a deployment means changing the `PYRITE_VERSION` arg and re-running the update script.

### CI Changes

- CI already runs on push to `main`. Extend to also run on `dev`.
- Consider adding a "release" workflow that automates the merge + tag + version bump.

### What This Does NOT Include

- **No PR reviews** — solo developer + AI agents, PRs add ceremony without value right now.
- **No release branches** — unnecessary at current scale. If a patch is needed, cherry-pick to `main` and tag.
- **No changelog generation** — keep it manual for now. Consider `git-cliff` later.
- **No branch protection rules** — trust-based for now. Revisit after announcement.

## Consequences

### Positive
- Live sites no longer break from untested development pushes
- Users can pin to a known-good version
- PyPI releases align with git tags
- Rollback is trivial: deploy the previous tag

### Negative
- Small overhead: merge `dev` → `main` when releasing
- Must remember to bump version after tagging
- Deploy scripts need the version arg updated for each upgrade

### Migration

1. Tag current `main` as `v0.21.0` (current pyproject.toml version is 0.20.0; we've added significant features since)
2. Create `dev` branch from `main`
3. Update deploy scripts to reference `v0.21.0`
4. Set GitHub default branch to `dev` (so PRs target `dev`)
5. Future development work goes to `dev`
