"""JSON encoding utilities."""

import json
from datetime import date, datetime
from pathlib import PurePath


class SafeEncoder(json.JSONEncoder):
    """JSON encoder that serializes date/datetime/Path objects safely."""

    def default(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if isinstance(o, PurePath):
            return str(o)
        return super().default(o)
