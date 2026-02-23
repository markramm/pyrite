"""JSON format serializer."""

import json
from typing import Any


def json_serialize(data: Any, **kwargs) -> str:
    """Serialize data to JSON string."""
    indent = kwargs.get("indent", 2)
    return json.dumps(data, indent=indent, default=str)
