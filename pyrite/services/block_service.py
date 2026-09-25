"""Block service: the blocks the indexer extracted from an entry's body.

The REST surface used to query the ``Block`` table itself, in two places
(``GET /entries/{id}/blocks`` and the fragment half of
``GET /entries/resolve``); both ask this service now (#380).
"""

from ..storage.database import PyriteDB
from ..storage.models import Block


class BlockService:
    """Read the ``block`` rows of an entry."""

    def __init__(self, db: PyriteDB):
        self.db = db

    def _query(
        self,
        entry_id: str,
        kb_name: str,
        heading: str | None,
        block_type: str | None,
        block_id: str | None,
    ):
        query = self.db.session.query(Block).filter_by(entry_id=entry_id, kb_name=kb_name)
        if heading:
            query = query.filter(Block.heading == heading)
        if block_type:
            query = query.filter(Block.block_type == block_type)
        if block_id:
            query = query.filter(Block.block_id == block_id)
        return query

    def list_blocks(
        self,
        entry_id: str,
        kb_name: str,
        *,
        heading: str | None = None,
        block_type: str | None = None,
        block_id: str | None = None,
    ) -> list[Block]:
        """The entry's blocks in body order, narrowed by any filter given."""
        return (
            self._query(entry_id, kb_name, heading, block_type, block_id)
            .order_by(Block.position)
            .all()
        )

    def find_block(
        self,
        entry_id: str,
        kb_name: str,
        *,
        heading: str | None = None,
        block_id: str | None = None,
    ) -> Block | None:
        """The first block matching a wikilink fragment, or ``None``."""
        return self._query(entry_id, kb_name, heading, None, block_id).first()
