"""IndexManager.is_empty: the check `pyrite search` and `pyrite index embed`
make before working on the index (#380 moved it off raw SQL / db calls)."""

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models.core_types import NoteEntry
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager


def test_is_empty_until_something_is_indexed(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="kb", path=kb, kb_type=KBType.GENERIC)],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(config.settings.index_path)
    try:
        mgr = IndexManager(db, config)
        assert mgr.is_empty() is True
        NoteEntry(id="n", title="N", body="b").save(kb / "n.md")
        mgr.index_all()
        assert mgr.is_empty() is False
    finally:
        db.close()
