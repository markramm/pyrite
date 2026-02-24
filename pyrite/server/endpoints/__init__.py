"""
Endpoint modules for the pyrite REST API.

Each module defines its own APIRouter. The routers are collected here
for inclusion by the application factory in api.py.
"""

from .admin import router as admin_router
from .daily import router as daily_router
from .entries import router as entries_router
from .kbs import router as kbs_router
from .search import router as search_router
from .settings_ep import router as settings_router
from .starred import router as starred_router
from .tags import router as tags_router
from .templates import router as templates_router
from .timeline import router as timeline_router
from .versions import router as versions_router

all_routers = [
    kbs_router,
    search_router,
    entries_router,
    timeline_router,
    tags_router,
    admin_router,
    starred_router,
    templates_router,
    daily_router,
    settings_router,
    versions_router,
]

__all__ = ["all_routers"]
