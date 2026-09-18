---
body: "## Problem\n\nPackage A built the deterministic e2e world with `PYRITE_AUTH_ENABLED=false`, so\n`verify_api_key` resolves every caller to `admin`. That makes the other specs\ndeterministic, but it leaves `web/e2e/auth.spec.ts` asserting on `/login` and\n`/register` in a world where auth is not the app's operating mode. A's own\n`fixtures.ts` names the open question and defers it to this package:\n\n> `/login` and `/register` are not the app's operating mode; auth specs must\n> either skip or run under their own auth-enabled project (package C).\n\nThis is the one package of the fan-out that carries a design decision rather\nthan a mechanical rewrite, and the decision is load-bearing for 0.24.2's\ndefinition of done: the web surface is only end-to-end tested if the login path\na real deployment uses is tested.\n\n## Decision to make\n\nEither (a) a second Playwright project with auth enabled, its own backend on its\nown port and its own seeded user, `testMatch`-partitioned so only `auth.spec.ts`\nruns under it; or (b) auth specs skip under the auth-disabled world, and the\nlogin path stays untested in CI. (a) is the one that makes the surface tested;\n(b) is only acceptable if (a) is shown to be disproportionate, with the reason\nrecorded.\n\n## Acceptance\n\n- [ ] A decision recorded in the spec file's header comment, with its reason.\n- [ ] `auth.spec.ts` asserts on the seeded world, with zero `text=` locators and\n      no `.first()` used to dodge strict mode.\n- [ ] Whatever it asserts passes 5x in a row.\n- [ ] Package A's four files stay the contract: `fixtures.ts`,\n      `global-setup.ts`, `seed.spec.ts` are read-only;\n      `playwright.config.ts` is edited only to add the second project, and only\n      under decision (a).\n\nPart of\n[[playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap]],\nPackage C. 0.24.2 definition of done — the web user surface."
file_path: /Users/markr/pyrite-wt/feature-playwright-package-c/kb/backlog/playwright-package-c-auth-spec-and-the-auth-enabled-project-decision.md
id: playwright-package-c-auth-spec-and-the-auth-enabled-project-decision
title: 'Playwright package C: auth.spec and the auth-enabled project decision'
type: backlog_item
tags:
- testing
- e2e
- web
- playwright
- auth
importance: 5
kind: task
status: done
priority: high
assignee: agent:pyrite-worker
effort: M
rank: 0
---

## Problem

Package A built the deterministic e2e world with `PYRITE_AUTH_ENABLED=false`, so
`verify_api_key` resolves every caller to `admin`. That makes the other specs
deterministic, but it leaves `web/e2e/auth.spec.ts` asserting on `/login` and
`/register` in a world where auth is not the app's operating mode. A's own
`fixtures.ts` names the open question and defers it to this package:

> `/login` and `/register` are not the app's operating mode; auth specs must
> either skip or run under their own auth-enabled project (package C).

This is the one package of the fan-out that carries a design decision rather
than a mechanical rewrite, and the decision is load-bearing for 0.24.2's
definition of done: the web surface is only end-to-end tested if the login path
a real deployment uses is tested.

## Decision to make

Either (a) a second Playwright project with auth enabled, its own backend on its
own port and its own seeded user, `testMatch`-partitioned so only `auth.spec.ts`
runs under it; or (b) auth specs skip under the auth-disabled world, and the
login path stays untested in CI. (a) is the one that makes the surface tested;
(b) is only acceptable if (a) is shown to be disproportionate, with the reason
recorded.

## Acceptance

- [ ] A decision recorded in the spec file's header comment, with its reason.
- [ ] `auth.spec.ts` asserts on the seeded world, with zero `text=` locators and
      no `.first()` used to dodge strict mode.
- [ ] Whatever it asserts passes 5x in a row.
- [ ] Package A's four files stay the contract: `fixtures.ts`,
      `global-setup.ts`, `seed.spec.ts` are read-only;
      `playwright.config.ts` is edited only to add the second project, and only
      under decision (a).

Part of
[[playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap]],
Package C. 0.24.2 definition of done — the web user surface.
