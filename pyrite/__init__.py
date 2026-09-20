"""pyrite: Knowledge-as-Code for you and your agents.

An open-source Knowledge Management System for structured markdown knowledge bases.
"""

import logging

# Applications decide where library logs go. The CLI replaces this inert
# handler with its own stderr handler at startup.
logging.getLogger(__name__).addHandler(logging.NullHandler())


def _read_version() -> str:
    """pyproject.toml is the one place the version is written.

    In a source checkout read it directly: an editable install's metadata goes
    stale at every bump until someone re-runs `pip install -e .`. Installed from
    a wheel there is no pyproject.toml beside the package, so ask the metadata.
    """
    import tomllib
    from importlib import metadata
    from pathlib import Path

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject.is_file():
        try:
            project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
            if project.get("name") == "pyrite" and project.get("version"):
                return project["version"]
        except (OSError, tomllib.TOMLDecodeError):
            pass
    try:
        return metadata.version("pyrite")
    except metadata.PackageNotFoundError:
        return "0+unknown"


__version__ = _read_version()
