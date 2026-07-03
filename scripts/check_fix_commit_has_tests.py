#!/usr/bin/env python3
"""Require `fix:`-prefixed commits to touch tests/ or extensions/*/tests/.

Mechanizes Iron Law 1 (no production code without a failing test first) at
the commit boundary -- a `fix:` commit with zero test lines is exactly the
class of regression the Iron Law exists to prevent (see 40e7a39, the fix
that shipped with zero test lines and this ticket's own motivation).

Used as a pre-commit `commit-msg` stage hook: receives the commit message
file path as argv[1], diffs the staged tree against HEAD, and exits
non-zero if the message starts with `fix:` but no staged file lives under
a tests/ directory.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def is_fix_commit(message: str) -> bool:
    """True if the commit message's subject line starts with `fix:`."""
    subject = message.strip().splitlines()[0] if message.strip() else ""
    return subject.startswith("fix:")


def touches_tests(changed_paths: list[str]) -> bool:
    """True if any changed path lives under a tests/ directory (top-level
    tests/ or extensions/*/tests/)."""
    return any("tests" in Path(path).parts for path in changed_paths)


def get_staged_paths() -> list[str]:
    """Paths staged for this commit, relative to the repo root."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    if len(sys.argv) < 2:
        print("check_fix_commit_has_tests: missing commit-msg file argument", file=sys.stderr)
        return 1

    message = Path(sys.argv[1]).read_text()
    if not is_fix_commit(message):
        return 0

    changed_paths = get_staged_paths()
    if touches_tests(changed_paths):
        return 0

    print(
        "ERROR: commit message starts with 'fix:' but no staged file is "
        "under a tests/ directory.\n"
        "  Iron Law 1: no production code without a failing test first.\n"
        "  If this fix genuinely has no testable behavior change (e.g. a\n"
        "  pure docs/config fix), reword the subject to drop the 'fix:'\n"
        "  prefix, or add the regression test the fix should have shipped\n"
        "  with.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
