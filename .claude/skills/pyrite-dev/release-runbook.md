# Release & Deploy Runbook

Procedural reference for the `dev → main` release path and the deploy script. SKILL.md keeps the daily-development rules (branches, committing); this file holds the runbook steps that only fire when shipping.

## Releasing (dev → main)

Only merge `dev` → `main` when the user explicitly asks to release.

```bash
# 1. Ensure CI is green on dev
# 2. Merge to main
git checkout main
git merge dev
# 3. Update version in pyproject.toml (remove .dev0 suffix)
# 4. Commit version bump
# 5. Tag
git tag -a v0.X.0 -m "v0.X.0: summary"
git push && git push --tags
# 6. Create GitHub release (triggers PyPI publish)
# 7. Switch back to dev and bump to next dev version
git checkout dev
# Edit pyproject.toml to 0.X+1.0.dev0
git commit -am "Bump version to 0.X+1.0.dev0"
git push
```

**PyPI**: triggered automatically by creating a GitHub release from a tag.

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

1. Cherry-pick the fix from `dev` to `main`
2. Bump patch version, tag (e.g., `v0.21.1`)
3. Deploy

## Site mapping (which branch lands where)

| Site | Source | Trigger |
|------|--------|---------|
| `demo.pyrite.wiki` | `dev` HEAD | Auto on CI pass |
| `capturecascade.org` | `main` tag | Manual via `deploy.sh cascade` |
| `pyrite.ink` | `main` tag | Manual via `deploy.sh ink <tag>` |
| PyPI | GitHub release from `main` tag | Auto on release publish |
