---
id: storage-invariants-harness-land-the-adr-0038-state-machine-with-strict-xfails
title: 'Storage invariants harness: land the ADR-0038 state machine with strict xfails'
type: backlog_item
tags:
- architecture
- storage
importance: 5
kind: tech_debt
status: proposed
priority: high
effort: S
rank: 0
---

Step 0 of [[adr-0038]] (proposed): land the storage-invariant harness before any fix, so each later step ends by deleting xfails.

## Acceptance criteria
- `tests/test_storage_invariants.py` from branch `spike/entry-identity-invariants` lands unchanged in substance: a Hypothesis `RuleBasedStateMachine` over a real KB, `PyriteDB`, `KBService`, `IndexManager`; one parametrized case per invariant I1-I9 plus three I10 git-history tests.
- `hypothesis==6.168.1` pinned exactly in the `dev` extra (`pyproject.toml`); derandomized runs depend on the version.
- Today's violations are strict xfails naming their issues: I1 #484, I2 #486/#487, I3 #485, I4 #483, I6 #488/#489, I7 #483, I8 #483/#484, I10 #489/#490. I5, I9 and the file_pattern I10 test pass.
- The file runs in under 60 s at `-n 4` (8 s measured on the spike).

## Footprint
`tests/test_storage_invariants.py`, `pyproject.toml`

**Model:** sonnet. **After:** #466 merged (the xfail set assumes its fixes).
