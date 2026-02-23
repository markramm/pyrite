"""Social KB preset definition."""

SOCIAL_PRESET = {
    "name": "my-community",
    "description": "Community knowledge base",
    "types": {
        "writeup": {
            "description": "User-authored writeup (essay, story, review, etc.)",
            "required": ["title"],
            "optional": ["writeup_type", "allow_voting"],
            "subdirectory": "writeups/",
        },
        "user_profile": {
            "description": "Community member profile",
            "required": ["title"],
            "optional": ["reputation", "join_date", "writeup_count"],
            "subdirectory": "users/",
        },
    },
    "policies": {
        "public": True,
        "author_edit_only": True,
        "minimum_reputation_to_post": 0,
        "voting_enabled": True,
    },
    "validation": {
        "enforce": True,
        "rules": [
            {
                "field": "writeup_type",
                "enum": ["essay", "story", "review", "howto", "opinion"],
            },
        ],
    },
    "directories": ["writeups", "users"],
}
