"""Encyclopedia KB preset definition."""

ENCYCLOPEDIA_PRESET = {
    "name": "our-encyclopedia",
    "description": "Collaborative encyclopedia",
    "types": {
        "article": {
            "description": "Encyclopedia article with quality assessment and review workflow",
            "required": ["title"],
            "optional": ["quality", "review_status", "protection_level", "categories"],
            "subdirectory": "articles/",
        },
        "talk_page": {
            "description": "Discussion page for an article",
            "required": ["title", "article_id"],
            "optional": [],
            "subdirectory": "talk/",
        },
    },
    "policies": {
        "public": True,
        "npov": True,
        "require_sources": True,
        "minimum_sources": 1,
        "review_required": True,
    },
    "validation": {
        "enforce": True,
        "rules": [
            {"field": "quality", "enum": ["stub", "start", "C", "B", "GA", "FA"]},
            {"field": "review_status", "enum": ["draft", "under_review", "published"]},
            {"field": "protection_level", "enum": ["none", "semi", "full"]},
        ],
    },
    "directories": ["articles", "talk", "drafts"],
}
