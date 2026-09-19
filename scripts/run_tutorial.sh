#!/usr/bin/env bash
# Run docs/getting-started.md as a test (docs-as-tests).
#
#   scripts/run_tutorial.sh                       # the getting-started tutorial
#   scripts/run_tutorial.sh docs/other-doc.md     # any doc with bash blocks
#
# A thin entry point: run_tutorial.py holds the logic (block extraction, the
# one persistent shell session, the temp HOME, the search-returns-results and
# index-health assertions) and this exists so CI and the test that pins the
# job have one stable command to call.
#
# The runner drives the INSTALLED package -- `pyrite` off PATH, the way a
# reader of the doc has it -- not the checkout, so install before running.
#
# PYRITE_TUTORIAL_VENV=/path/to/venv runs the tutorial against THAT venv
# instead of the repo's. scripts/release.py sets it to the throwaway venv it
# installed the release SHA into, so the release check exercises what a user
# gets rather than the checkout. Unset (the CI and developer case), nothing
# changes.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "${PYRITE_TUTORIAL_VENV:-}" ]; then
  if [ ! -x "${PYRITE_TUTORIAL_VENV}/bin/python" ]; then
    echo "PYRITE_TUTORIAL_VENV=${PYRITE_TUTORIAL_VENV} has no bin/python" >&2
    exit 1
  fi
  PATH="${PYRITE_TUTORIAL_VENV}/bin:$PATH"
  export PATH
  exec "${PYRITE_TUTORIAL_VENV}/bin/python" "$here/run_tutorial.py" "$@"
fi

# Prefer the repo's venv when there is one and nothing else is active; a bare
# `python3` on a developer machine usually has no pyrite installed.
python_bin="python3"
if [ -z "${VIRTUAL_ENV:-}" ] && [ -x "$here/../.venv/bin/python" ]; then
  python_bin="$here/../.venv/bin/python"
  PATH="$here/../.venv/bin:$PATH"
  export PATH
fi

exec "$python_bin" "$here/run_tutorial.py" "$@"
