"""pytest plugin that scripts/verify_red_ci.py loads into both of its runs.

It keeps only the tests the driver asks for (``VERIFY_RED_SELECT``: a JSON list
of ``[file, class..., function]`` keys) and appends one JSON line per report to
``VERIFY_RED_RECORD`` as it happens, so a run killed by the driver's timeout
still leaves what it finished. A failure is recorded from the exception object
itself -- its type's MRO and its ``args`` -- never from a traceback, so
the repo's ``--tb`` setting cannot change a verdict.
"""

from __future__ import annotations

import json
import os

import pytest


def _write(record: dict) -> None:
    with open(os.environ["VERIFY_RED_RECORD"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def key(nodeid: str) -> tuple[str, ...]:
    """``tests/x.py::TestA::test_b[1]`` -> ``("tests/x.py", "TestA", "test_b")``."""
    return tuple(nodeid.split("[", 1)[0].split("::"))  # a parameter id may hold "::"


def pytest_configure(config: pytest.Config) -> None:
    # Registered here too: the run without the fix may use a pyproject from
    # before the marker existed, and --strict-markers would stop it.
    config.addinivalue_line("markers", "control: a deliberate negative control")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    with open(os.environ["VERIFY_RED_SELECT"], encoding="utf-8") as fh:
        wanted = {tuple(k) for k in json.load(fh)}
    keep = [i for i in items if key(i.nodeid) in wanted]
    drop = [i for i in items if key(i.nodeid) not in wanted]
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep


def pytest_collectreport(report: pytest.CollectReport) -> None:
    if report.failed:
        _write({"collect": report.nodeid})


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    report = yield
    record = {
        "nodeid": item.nodeid,
        "when": call.when,
        "outcome": report.outcome,
        "control": item.get_closest_marker("control") is not None,
    }
    if report.failed and call.excinfo is not None:
        exc = call.excinfo.value
        record["exc"] = {
            "types": [c.__name__ for c in type(exc).__mro__],
            "args": [a for a in exc.args if isinstance(a, str)],
        }
    _write(record)
    return report
