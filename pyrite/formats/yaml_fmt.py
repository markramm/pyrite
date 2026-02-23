"""YAML format serializer."""

from typing import Any


def yaml_serialize(data: Any, **kwargs) -> str:
    """Serialize data to YAML."""
    from pyrite.utils.yaml import dump_yaml

    if isinstance(data, dict):
        return dump_yaml(data)
    return str(data)
