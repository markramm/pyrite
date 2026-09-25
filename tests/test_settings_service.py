"""SettingsService: the instance settings store, behind a service (#380).

The REST settings endpoints used to reach ``svc.db.*`` through a
``KBService``; they now go through this service. The contract is the one
the endpoints relied on: ``get`` answers ``None`` for a missing key, ``set``
upserts, ``all`` is a plain dict, ``delete`` says whether a row went.
"""

import pytest

from pyrite.services.settings_service import SettingsService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def settings(tmp_path):
    db = PyriteDB(tmp_path / "index.db")
    yield SettingsService(db)
    db.close()


def test_get_missing_is_none(settings):
    assert settings.get("ui.theme") is None


def test_set_then_get(settings):
    settings.set("ui.theme", "dark")
    assert settings.get("ui.theme") == "dark"


def test_set_upserts(settings):
    settings.set("ui.theme", "dark")
    settings.set("ui.theme", "light")
    assert settings.get("ui.theme") == "light"
    assert settings.all() == {"ui.theme": "light"}


def test_all_is_every_setting(settings):
    assert settings.all() == {}
    settings.set("a", "1")
    settings.set("b", "2")
    assert settings.all() == {"a": "1", "b": "2"}


def test_delete_reports_whether_a_row_went(settings):
    settings.set("a", "1")
    assert settings.delete("a") is True
    assert settings.get("a") is None
    assert settings.delete("a") is False
