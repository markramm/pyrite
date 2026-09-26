---
id: scope-parameters-are-required-forgetting-one-fails-closed
title: 'Scope parameters are required: forgetting one fails closed'
type: standard
tags:
- security
- standards
importance: 5
---

Maintainer decision, 2026-09-26, from batch 3b C1's cold read.

A parameter that narrows what a caller may see, such as readable_kbs, the ReadScope or a principal, is never optional with an unscoped default. A call that forgets it must fail: raise, fail a type check or a structural test, and never silently see everything. Unscoped callers (the CLI, admin, operator key, local stdio) say so explicitly, with a named sentinel such as UNSCOPED.

Why: in C1, three leaks remained after the ticketed paths were fixed (MCP kb_qa_status, task-id resolution, link discovery). Each was a caller that never passed readable_kbs, which defaulted to None, meaning unscoped. A name-list guard missed all three.

How to apply: new service, storage and plugin read APIs take the scope as a required keyword argument. Reviews treat `readable_kbs=None` as a default, or a `param: X | None = None` for scope, as a finding.
