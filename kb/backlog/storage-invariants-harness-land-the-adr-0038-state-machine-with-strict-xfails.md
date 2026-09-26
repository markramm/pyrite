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
- `tests/test_storage_invariants.py` from PR #492 lands unchanged in substance, in two layers:
  - one hand-written strict xfail per known violation (`raises=AssertionError`, message prefix `I<n>:`, one issue each): I1 #484; I2 #486, #487, #495; I3 #485; I4 #483; I6 #488, #489; I7 #483; I8 #483, #484; I9 #493, #494; I10 #489, #490;
  - an exploratory `RuleBasedStateMachine` run over a real KB, pinned with `@seed(20260925)`, 150 × 20 steps, checking I5 and I9 (the known I9 shapes excluded by state).
- Mutations M1 (create may overwrite), M2 (update skips the index) and M3 (delete keeps the row) each turn the exploratory run red.
- The file runs in under 30 s at `-n 4` (about 10 s measured).

## Footprint
`tests/test_storage_invariants.py`, `pyproject.toml`

**Model:** sonnet. **After:** #466 merged (the xfail set assumes its fixes).
