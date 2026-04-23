"""Public SEO endpoints: /sitemap.xml and /robots.txt.

Mounted outside /api (no auth) so crawlers can reach them without
signing in. The site URL for canonical links comes from the branding
config's site_url field when set; otherwise the response uses
path-only URLs that resolve relative to whatever host served them.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from ..config import PyriteConfig
from ..services.branding_service import BrandingService
from ..services.sitemap_service import SitemapService
from ..storage.database import PyriteDB
from .api import get_config, get_db

seo_router = APIRouter(tags=["SEO"])


def _site_url(config: PyriteConfig) -> str:
    brand = BrandingService(config.settings.branding_dir).get()
    return brand.site_url or ""


@seo_router.get("/sitemap.xml")
def sitemap_xml(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> Response:
    """Return the sitemap XML document."""
    svc = SitemapService(config, db)
    xml = svc.render_xml(_site_url(config))
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@seo_router.get("/robots.txt")
def robots_txt(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> Response:
    """Return robots.txt pointing at the sitemap."""
    svc = SitemapService(config, db)
    return Response(
        content=svc.render_robots(_site_url(config)),
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=3600"},
    )
