"""Seed web users for tests, the way an operator would.

Before #13 a test world got its admin by registering first, and every later
registrant read every KB through the global ``read`` role. Neither holds any
more: registration is refused until an admin exists, and a self-registered
user reads public KBs only. Tests whose subject is *not* sign-up use these
helpers to build the same world through the operator path
(``AuthService.create_user``, what ``pyrite-admin user create`` calls):

- the first user seeded into a database is ``admin``;
- later users get ``read`` with their role covering every KB, which is what
  a registrant used to get.

Tests about registration itself call ``/auth/register`` or
``AuthService.register`` directly.
"""

from __future__ import annotations

from pyrite.config import AuthConfig
from pyrite.services.auth_service import AuthService
from pyrite.storage.database import PyriteDB

SESSION_COOKIE = "pyrite_session"


def seed_user(
    db: PyriteDB,
    username: str,
    password: str = "password123",
    *,
    role: str | None = None,
    display_name: str | None = None,
) -> dict:
    """Create a user: admin when the database has none yet, else ``read``."""
    service = AuthService(db, AuthConfig(enabled=True))
    if role is None:
        role = "read" if service.admin_exists() else "admin"
    return service.create_user(username, password, role=role, display_name=display_name)


def app_db(app) -> PyriteDB:
    """The PyriteDB an app's requests use (a test's ``get_db`` override, or
    the app's own)."""
    from pyrite.server.api import get_db

    override = app.dependency_overrides.get(get_db)
    if override is not None:
        db = override()
        if isinstance(db, PyriteDB):  # not create_app's own generator dependency
            return db
    db = getattr(app.state, "pyrite_db", None)
    if db is None:
        raise RuntimeError("app has no PyriteDB yet; seed through a PyriteDB directly")
    return db


def sign_in(app, username: str, password: str = "password123") -> str:
    """A session token for an existing user, without going through
    ``/auth/login`` (and so without spending its rate limit)."""
    from pyrite.server.api import get_config

    override = app.dependency_overrides.get(get_config)
    config = override() if override is not None else app.state.pyrite_config
    _, token = AuthService(app_db(app), config.settings.auth).login(username, password)
    return token


def seed_and_sign_in(
    client,
    username: str,
    password: str = "password123",
    *,
    role: str | None = None,
    display_name: str | None = None,
) -> dict:
    """Seed a user in ``client``'s app and put their session cookie on
    ``client``. Returns the user dict (what ``/auth/register`` returned)."""
    user = seed_user(app_db(client.app), username, password, role=role, display_name=display_name)
    client.cookies.set(SESSION_COOKIE, sign_in(client.app, username, password))
    return user
