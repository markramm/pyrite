"""Public SEO endpoints: /sitemap.xml and /robots.txt.

Mounted outside /api (no auth) so crawlers can reach them without
signing in. The site URL for canonical links comes from the branding
config's site_url field when set; otherwise the response uses
path-only URLs that resolve relative to whatever host served them.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response

from ..config import PyriteConfig
from ..exceptions import BrandingInvalidError
from ..services.branding_service import BrandingService
from ..services.sitemap_service import SitemapService
from .api import get_config, get_sitemap_service

logger = logging.getLogger(__name__)

seo_router = APIRouter(tags=["SEO"])


def _site_url(config: PyriteConfig) -> str:
    """The branding config's site_url, or "" (path-only URLs) on failure.

    A crawler reading a 5xx on /robots.txt takes it as "don't crawl" -- an
    operator's config typo must not pull the whole site out of search
    (#445 delta cold read). Unlike POST /api/site/render (a deliberate
    operator action answered with 409 BRANDING_INVALID) and
    GET /config/branding (kept at 500; the web branding store already has
    a fallback for it), these two anonymous, always-on routes degrade to
    default branding instead of failing. BrandingService._load itself
    logs the failure once per (path, mtime), so this call site does not
    need its own log line.
    """
    try:
        brand = BrandingService(config.settings.branding_dir).get()
    except BrandingInvalidError:
        return ""
    return brand.site_url or ""


@seo_router.get("/sitemap.xml")
def sitemap_xml(
    config: PyriteConfig = Depends(get_config),
    svc: SitemapService = Depends(get_sitemap_service),
) -> Response:
    """Return the sitemap XML document."""
    xml = svc.render_xml(_site_url(config))
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@seo_router.get("/robots.txt")
def robots_txt(
    config: PyriteConfig = Depends(get_config),
    svc: SitemapService = Depends(get_sitemap_service),
) -> Response:
    """Return robots.txt pointing at the sitemap."""
    return Response(
        content=svc.render_robots(_site_url(config)),
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=3600"},
    )
