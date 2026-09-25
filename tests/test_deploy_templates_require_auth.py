"""The one-click deploy templates start a server that requires a credential.

Render, Fly.io and Railway put the app on a public hostname. A server there
with auth disabled and no API keys would make every visitor admin -- and the
Host guard (pyrite/server/request_guard.py) refuses every request addressed to
a name it was not told about. So each template turns auth on; the operator
registers the first account (the first registered user is admin).
"""

import json
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _truthy(value) -> bool:
    return str(value).lower() in ("true", "1", "yes")


def test_render_template_enables_auth():
    doc = yaml.safe_load((ROOT / "render.yaml").read_text())
    env = {v["key"]: v.get("value") for v in doc["services"][0]["envVars"]}
    assert _truthy(env.get("PYRITE_AUTH_ENABLED")), env


def test_fly_template_enables_auth():
    doc = tomllib.loads((ROOT / "fly.toml").read_text())
    assert _truthy(doc["env"].get("PYRITE_AUTH_ENABLED")), doc["env"]


def test_railway_template_defaults_auth_on():
    """railway.json has no env block; the start command defaults the variable
    to true while still letting the dashboard override it."""
    doc = json.loads((ROOT / "railway.json").read_text())
    command = doc["deploy"]["startCommand"]
    assert "pyrite-server" in command
    assert _railway_env(command, {}) == "true"
    assert _railway_env(command, {"PYRITE_AUTH_ENABLED": "false"}) == "false"


def _railway_env(command: str, env: dict) -> str:
    """Run the start command with `pyrite-server` swapped for a probe that
    prints what the server process would see."""
    import os
    import shlex
    import subprocess

    probe = command.replace("pyrite-server", "printenv PYRITE_AUTH_ENABLED")
    base = {k: v for k, v in os.environ.items() if k != "PYRITE_AUTH_ENABLED"}
    out = subprocess.run(
        shlex.split(probe), env={**base, **env}, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()
