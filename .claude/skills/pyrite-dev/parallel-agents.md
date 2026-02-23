# Parallel Agent Protocol

How to safely launch, coordinate, and merge work from multiple Claude Code agents.

## Isolation Strategy: Don't Use Worktrees

**Do NOT use `isolation: "worktree"` for short-lived parallel agents.** Learned from Wave 3A:

- Worktrees branch from HEAD at creation, but the base commit is unreliable — one agent branched from a commit 10+ commits behind HEAD despite main being clean
- Worktree diffs against main show hundreds of spurious "deleted" files when the base is wrong
- The merge ceremony (copy new files, read diffs, patch shared files) adds significant overhead
- An agent that worked directly on main (no worktree) produced the cleanest, most mergeable result

**Instead:** Launch agents without isolation. Rely on **file footprint planning** to prevent conflicts. Agents write directly to the working tree. Since we validate that no two agents touch the same file, there are no conflicts to resolve.

### When Worktrees Make Sense

Worktrees are appropriate for:
- Long-lived feature branches that will be PR'd
- Agents working on genuinely risky/experimental changes you might discard
- Cases where you need rollback isolation (agent might break the build)

For our typical "launch 3 agents, merge in 5 minutes" workflow, they add cost without benefit.

## Wave Planning Rules

Before launching parallel agents, validate:

1. **File footprint**: Each wave item must list files it will create or modify
2. **No shared modified files**: If two items share a modified file, either:
   - One item waits for the next wave
   - The shared file is split first (like the `api.py` -> `endpoints/` extraction)
3. **Max 3 parallel agents**: Diminishing returns past 3 due to context and review overhead
4. **New-file-only items are always safe**: Items that only create new files can always parallelize

### Example Wave Validation

```
Wave candidates:
  #10 Research Flow Skill — creates: skills/research-flow/  modifies: nothing
  #12 Backlinks Panel    — creates: BacklinksPanel.svelte   modifies: +page.svelte, ui.svelte.ts
  #14 Slash Commands     — creates: slash-commands.ts        modifies: setup.ts, Editor.svelte

No overlap between #10, #12, and #14 -> safe to parallelize all three.

If #12 and #14 both modified +layout.svelte:
FIX: Run #10 + #12 in parallel. #14 waits or runs after #12 commits.
```

## Agent Launch Checklist

```
- [ ] All pending work committed to main
- [ ] File footprints validated — no two agents modify the same file
- [ ] Agent prompt specifies which files are NEW vs EXISTING
- [ ] Agent prompt lists exact files for EXISTING modifications
- [ ] Do NOT use isolation: "worktree" (see above)
```

### Writing Effective Agent Prompts

**Bad prompt** (leads to clobber):
> "Add starred entries feature with API endpoints, DB model, and UI components"

**Good prompt** (explicit file list):
> "Add starred entries feature. Create these NEW files:
> - `pyrite/server/endpoints/starred.py` (new endpoint module)
> - `pyrite/storage/models.py` (new ORM model)
> - `web/src/lib/StarredPanel.svelte` (new component)
>
> EXISTING files to patch (do NOT rewrite — only add minimal changes):
> - `pyrite/server/endpoints/__init__.py` — add import for starred router
> - `web/src/routes/+layout.svelte` — add StarredPanel import and instance"

## Merge Protocol

Since agents work directly on main without worktrees:

### 1. Verify no conflicts after agents complete

```bash
git status -s                    # See all changes
git diff --stat                  # Summarize what changed
```

### 2. Review and test each agent's work

For each agent, in order of fewest shared file modifications:

```bash
# Lint
.venv/bin/ruff check <modified python files>

# Test
.venv/bin/pytest tests/ -x -q
cd web && npm run build          # if frontend touched
```

### 3. Commit each agent's work separately

```bash
git add <agent's specific files>
git commit -m "Implement #N: description"
```

Commit one agent at a time. Run tests between commits. This gives clean rollback points.

### 4. If something breaks

Since all changes are on main, use `git checkout -- <file>` to revert specific files, or `git stash` to save everything and debug.

## The Three Failure Modes

| Failure | Root cause | Prevention |
|---------|-----------|------------|
| Stale code | Agents branched from wrong commit (worktree bug) | Don't use worktrees |
| File contention | Multiple agents modify same file | Wave planning with file footprints |
| Clobber on merge | Wholesale file copy from worktree | Agents write directly; no merge needed |

## Lessons Learned (Wave 3A)

- Agent with `isolation: "worktree"` branched from commit `d994de2` (10+ commits behind HEAD). The resulting diff showed 200+ spurious deletions. Required manual extraction of just the relevant changes.
- Second worktree agent branched correctly but still required copy+patch ceremony.
- Third agent got no worktree at all (mechanism silently failed). It wrote to main directly, which was the cleanest outcome — changes were right there, no merge gymnastics.
- **Conclusion**: File footprint planning is the real safety mechanism. Worktree isolation is redundant overhead for this workflow.
