---
id: kb-packaging-and-distribution-for-pre-populated-research-kbs
title: KB Packaging and Distribution for Pre-Populated Research KBs
type: backlog_item
tags:
- deployment
- journalism
- kb-management
links:
- target: epic-journalists-pyrite-wiki-hosted-research-platform-for-independent-journalists
  relation: subtask_of
  kb: pyrite
importance: 5
---

## Problem

The pre-populated KBs (Capture Timeline, Thiel Network, etc.) need to be packaged for deployment to the hosted instance and potentially for other users to self-host. Currently KBs are just git repos with no standardized distribution mechanism.

## Solution

1. **KB packaging format** -- A standard way to bundle a KB (git repo + kb.yaml + index metadata) for deployment
2. **KB registry entries** -- Each distributable KB registered with name, description, source repo, and access tier
3. **KB provisioning on instance setup** -- Script/command to clone and index all pre-populated KBs on a fresh instance
4. **Cross-KB link validation** -- Verify that cross-KB links resolve correctly when KBs are deployed together
5. **KB versioning** -- Track which version of each pre-populated KB is deployed, support updates

### KBs to Package

- cascade-timeline (4781 entries)
- cascade-research (377 entries)
- cascade-solidarity (267 entries)
- thiel-network (108 entries)
- epstein-network (216 entries)
- surveillance-industrial-complex (173 entries)

Total: ~5,922 entries across 6 KBs.

## Success Criteria

- Single command deploys all 6 KBs to a fresh instance
- Cross-KB links resolve correctly
- KBs can be updated independently without breaking links
