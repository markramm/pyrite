"""Zettelkasten KB preset definition."""

ZETTELKASTEN_PRESET = {
    "name": "my-zettelkasten",
    "description": "Personal knowledge garden",
    "types": {
        "zettel": {
            "description": "Atomic knowledge note",
            "required": ["title"],
            "optional": ["zettel_type", "maturity", "source_ref", "processing_stage"],
            "subdirectory": "zettels/",
        },
        "literature_note": {
            "description": "Note capturing ideas from a source work",
            "required": ["title", "source_work"],
            "optional": ["author", "page_refs"],
            "subdirectory": "literature/",
        },
    },
    "policies": {
        "private": True,
        "single_author": True,
    },
    "validation": {
        "enforce": True,
        "rules": [
            {"field": "zettel_type", "enum": ["fleeting", "literature", "permanent", "hub"]},
            {"field": "maturity", "enum": ["seed", "sapling", "evergreen"]},
            {
                "field": "processing_stage",
                "enum": ["capture", "elaborate", "question", "review", "connect"],
            },
        ],
    },
    "directories": ["zettels", "literature"],
}
