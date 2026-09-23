---
id: the-pr-gate-runs-one-interpreter-so-a-test-infrastructure-change-that-breaks
title: The PR gate runs one interpreter, so a test-infrastructure change that breaks only on 3.13 merges green and reddens dev — and a cold read's 'I could not confirm this' was filed as a trade-off
type: backlog_item
tags:
- process
importance: 5
status: done
priority: medium
rank: 0
---

PR #81 merged with every check green and its push to `dev` went red two minutes later: `test (3.13)` — `fixture 'read_only_client' not found`, six errors in `tests/test_api_tiers.py`. Fixed forward by a peer session in `cb7e7fa`.

The PR gate runs **one** interpreter (3.12); the full matrix runs on the `dev` push. That is a deliberate trade for speed and it is right for most changes. It is wrong for one specific class, and this is the evidence.

## What broke

Five class-scoped fixtures were changed to `@classmethod` stacked above `@pytest.fixture` (clearing a pytest deprecation warning). On 3.12 this registers and works. **On 3.13 it silently does not register the fixture at all** — no import error, no warning; the fixture is simply absent, so every test requesting it errors at setup.

## Why review did not catch it

It was caught — by the cold read, in these words:

> `@classmethod` over `@pytest.fixture` is an ordering pytest does not document as supported, and the project pins only `pytest>=8.0.0` — **I could not confirm the combination on pytest 8.**

The conductor read that, verified the fixtures ran on the local interpreter, and carried it into the PR body as a *known trade-off*. It was not a trade-off. **A trade-off is a cost you have measured and chosen; an unknown is not a trade-off.** The one environment the finding could not be confirmed in is exactly where it broke.

## Two changes worth making

1. **Run the matrix on the PR when the diff changes how tests are declared or collected.** A `conftest.py` fixture, a decorator contract, fixture scope, collection hooks, `pyproject.toml`'s pytest config — anything pytest itself resolves rather than the code under test. These are precisely the changes whose behaviour is a property of the *interpreter and pytest version*, not of the project's logic, so a single-interpreter gate cannot see them. The existing `changes` classifier already routes by path; this is one more rule in it.

2. **A cold-read finding that says "I could not confirm X" is not dischargeable as a trade-off.** The options are: confirm it, remove the dependency on it, or hold the PR. Worth a line in `review.md` next to the cold-read section, because the failure mode is subtle — the finding *was* surfaced, *was* read, and *was* written into the PR body, and the process still shipped it. In this case the `@classmethod` change was incidental to the theme (it cleared an unrelated deprecation warning), so the cheapest correct action was simply to drop it.

Related: the cold read on PR #81; #103 (the conflicted-PR-gets-no-checks failure, same "the gate cannot see it" family); retro 2's rule that a report's numbers must be measured under one interpreter with the tree pinned — this is the same lesson from the other direction, that *one* interpreter is not enough for some diffs.


## Triage 2026-09-20 (from GitHub)

**State: still open for a reason — leave open.** (`process` issue; verified, not rewritten.)

Change 1 is **not** made. `.github/workflows/ci.yml:99` still reads:

```
python-version: ${{ fromJSON(github.event_name == 'pull_request' && '["3.12"]' || '["3.11", "3.12", "3.13"]') }}
```

— one interpreter on a PR, the full matrix only on the `dev` push, for every diff without exception. The `changes` classifier does already have a `conftest.py` path entry (`:54`), so the routing hook this issue proposes exists; nothing uses it to widen the matrix.

Change 2 (a cold-read "I could not confirm X" is not dischargeable as a trade-off) is **not** in `review.md` either — the cold-read section covers when to dispatch one and what to look for, not how to triage a finding of that shape.

Both remain live, and change 2 is one sentence in `review.md`. Worth noting that #115 is the same seam from the other side — what the reviewer is allowed to be told, and what a conductor may do with what it says.


_Migrated from GitHub issue #133 on 2026-09-20 (maintainer: process findings live in the KB)._

## Done 2026-09-23 (retro 8)

Fixed by #206 (merged 2026-09-20); verified on dev at 6e505be. Left `proposed` for three days because nothing moves a KB item when the PR that fixes it merges.
