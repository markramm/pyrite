#!/usr/bin/env python3
"""Warn when a pull request changes behaviour but records no changelog fragment.

`#276` moved changelog entries to one file per change under `changelog.d/`.
Nothing checked that a pull request actually adds one, and the gap produced a
real miss within the hour: #173 merged with its entry appended to `CHANGELOG.md`
under the already-released `## [0.24.3]` heading, so it was absent from the
release notes `scripts/release.py` assembles and nothing complained. The
existing `tests/test_changelog_fragments.py` guards the invariant that
`[Unreleased]` stays empty -- which it was -- and cannot see a pull request
that adds nothing at all (#278).

**This warns; it does not fail.** Not every change needs a fragment, the
judgement is genuinely the author's, and a blocking check that first-time
contributors hit on their first pull request is the friction #276 existed to
remove. Six `CHANGELOG.md` conflicts in a week, half of them on newcomers'
branches, is what this area already cost people.

The rule:

  a fragment is EXPECTED when the diff touches shipped code
  (`pyrite/` or `extensions/`), because that is what a user could notice;

  it is NOT expected for anything else -- tests, CI, docs, the KB, skills --
  matching the exemptions `changelog.d/README.md` already documents;

  and `Changelog: none` in the pull-request body overrides the inference, for
  the refactor-with-no-behaviour-change case the README also allows.

Usage:
    check_changelog_fragment.py --base <sha> --head <sha> [--body-file <path>]

Exit status is always 0: this is advisory. It prints a GitHub Actions warning
annotation when a fragment looks missing.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

# Touching these means a user could notice the change.
SHIPPED_CODE_PREFIXES = ("pyrite/", "extensions/")

# Files that live in changelog.d/ without being entries. Mirrors
# scripts/release.py's FRAGMENT_NON_ENTRIES; a test asserts they agree.
FRAGMENT_NON_ENTRIES = frozenset({"README.md", ".gitkeep", ".gitignore"})

# An explicit opt-out in the PR body, e.g. "Changelog: none (pure refactor)".
OPT_OUT = re.compile(r"^\s*changelog:\s*none\b", re.IGNORECASE | re.MULTILINE)


def changed_files(base: str, head: str) -> list[str]:
    """Files changed between two commits, or [] if the range cannot be read."""
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...{head}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line for line in out.splitlines() if line]


def adds_fragment(files: list[str]) -> bool:
    """True when the diff adds a real fragment.

    `changelog.d/README.md` is documentation, not an entry. The exclusion set
    mirrors `scripts/release.py`'s `FRAGMENT_NON_ENTRIES`, which skips the same
    files when assembling the notes -- if this disagreed with that, a PR could
    be told it had recorded a change that the release would not report. Without
    it, a PR editing the README alongside its code silences the check.
    """
    return any(
        f.startswith("changelog.d/")
        and f.endswith(".md")
        and f.rsplit("/", 1)[-1] not in FRAGMENT_NON_ENTRIES
        for f in files
    )


def touches_shipped_code(files: list[str]) -> bool:
    return any(f.startswith(SHIPPED_CODE_PREFIXES) for f in files)


def opted_out(body: str) -> bool:
    return bool(OPT_OUT.search(body or ""))


def verdict(files: list[str], body: str) -> str | None:
    """The warning to print, or None when nothing should be said.

    Kept free of I/O so the decision itself is directly testable.
    """
    if not files:
        return None
    if adds_fragment(files):
        return None
    if opted_out(body):
        return None
    if not touches_shipped_code(files):
        return None
    changed = [f for f in files if f.startswith(SHIPPED_CODE_PREFIXES)]
    shown = ", ".join(changed[:3]) + (" ..." if len(changed) > 3 else "")
    return (
        f"This PR changes shipped code ({shown}) but adds no changelog.d/ "
        "fragment, so the change will not appear in the release notes. Add "
        "changelog.d/<slug>.<section>.md (see changelog.d/README.md), or put "
        "'Changelog: none' in the PR description if no user would notice this "
        "change."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--body-file", default=None)
    args = parser.parse_args()

    body = ""
    if args.body_file:
        try:
            with open(args.body_file, encoding="utf-8") as handle:
                body = handle.read()
        except OSError:
            body = ""

    message = verdict(changed_files(args.base, args.head), body)
    if message:
        # A GitHub Actions warning annotation: visible on the PR, not blocking.
        print(f"::warning title=No changelog fragment::{message}")
    else:
        print("changelog fragment check: nothing to flag")
    return 0


if __name__ == "__main__":
    sys.exit(main())
