"""
Static file serving for the Pyrite web application.

Serves the built SvelteKit app from web/dist/ with SPA fallback:
- /site/* → pre-rendered static HTML from site-cache/ (SEO-friendly)
- /site/sitemap.xml → dynamic sitemap from index
- /site/robots.txt → crawler directives
- /assets/* → static files (JS, CSS, images)
- /api/* → handled by API router (not intercepted here)
- Everything else → index.html (SPA client-side routing)
"""

import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles


def mount_site_routes(app: FastAPI) -> None:
    """Mount /site and /viewer routes. These work independent of the SPA dist."""
    data_dir = Path(os.environ.get("PYRITE_DATA_DIR", "."))
    site_cache_dir = data_dir / "site-cache"
    viewer_dir = data_dir / "viewer"

    # Sitemap
    @app.get("/site/sitemap.xml", include_in_schema=False)
    async def sitemap(request: Request):
        return _generate_sitemap(site_cache_dir, str(request.base_url).rstrip("/"))

    # Robots.txt
    @app.get("/site/robots.txt", include_in_schema=False)
    @app.get("/robots.txt", include_in_schema=False)
    async def robots(request: Request):
        base = str(request.base_url).rstrip("/")
        body = f"User-agent: *\nAllow: /site/\nDisallow: /api/\nDisallow: /auth/\n\nSitemap: {base}/site/sitemap.xml\n"
        return Response(content=body, media_type="text/plain")

    # Serve /viewer/* from data/viewer/ directory
    @app.get("/viewer/{path:path}", include_in_schema=False)
    async def viewer_page(request: Request, path: str):
        return _serve_static_dir(viewer_dir, path, fallback_spa=True)

    @app.get("/viewer", include_in_schema=False)
    async def viewer_index(request: Request):
        return _serve_static_dir(viewer_dir, "index.html")

    # Search page
    @app.get("/site/search", include_in_schema=False)
    async def site_search(request: Request):
        return _serve_search_page(site_cache_dir)

    # Serve /site/* from pre-rendered cache
    @app.get("/site/{path:path}", include_in_schema=False)
    async def site_page(request: Request, path: str):
        return _serve_site_cached(site_cache_dir, path, "<html><body>Page not yet rendered. Run site cache render.</body></html>")

    @app.get("/site", include_in_schema=False)
    async def site_index(request: Request):
        return _serve_site_cached(site_cache_dir, "", "<html><body>Site not yet rendered. Run site cache render.</body></html>")


def mount_static(app: FastAPI, dist_dir: Path) -> None:
    """Mount SPA static file serving with fallback.

    Args:
        app: The FastAPI application instance.
        dist_dir: Path to web/dist/ directory containing built SvelteKit output.
    """
    index_html = dist_dir / "index.html"
    if not index_html.exists():
        return

    index_content = index_html.read_text()

    # Mount the assets directory for hashed static files
    assets_dir = dist_dir / "_app"
    if assets_dir.is_dir():
        app.mount("/_app", StaticFiles(directory=str(assets_dir)), name="svelte-app")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        favicon_path = dist_dir / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(str(favicon_path))
        return HTMLResponse(status_code=404)

    # SPA fallback — catch all non-API, non-site, non-viewer routes
    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(request: Request, path: str):
        if path.startswith(("api/", "docs", "redoc", "openapi.json", "health", "auth/", "site", "viewer")):
            return HTMLResponse(status_code=404)

        file_path = dist_dir / path
        if file_path.is_file() and file_path.resolve().is_relative_to(dist_dir.resolve()):
            return FileResponse(str(file_path))

        # SPA index.html must not be cached — it references hashed JS chunks
        # that change on each build. Stale index.html = mismatched chunk errors.
        return HTMLResponse(
            content=index_content,
            headers={"Cache-Control": "no-cache"},
        )


def _serve_static_dir(
    directory: Path, path: str, fallback_spa: bool = False
) -> HTMLResponse | FileResponse:
    """Serve a file from a static directory, with optional SPA fallback."""
    if not directory.is_dir():
        return HTMLResponse(status_code=404)

    file_path = directory / path
    try:
        resolved = file_path.resolve()
        if not resolved.is_relative_to(directory.resolve()):
            return HTMLResponse(status_code=404)
    except (ValueError, OSError):
        return HTMLResponse(status_code=404)

    if file_path.is_file():
        return FileResponse(str(file_path))

    # SPA fallback — serve index.html for client-side routing
    if fallback_spa:
        index = directory / "index.html"
        if index.is_file():
            return FileResponse(str(index))

    return HTMLResponse(status_code=404)


def _generate_sitemap(cache_dir: Path, base_url: str) -> Response:
    """Generate sitemap.xml from cached HTML files."""
    urls = []

    if not cache_dir.is_dir():
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n</urlset>'
        return Response(content=xml, media_type="application/xml")

    # Landing page
    if (cache_dir / "index.html").exists():
        urls.append(f"  <url>\n    <loc>{base_url}/site</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>")

    # Walk KB directories
    for kb_dir in sorted(cache_dir.iterdir()):
        if not kb_dir.is_dir():
            continue
        kb_name = kb_dir.name

        # KB index
        if (kb_dir / "index.html").exists():
            urls.append(f"  <url>\n    <loc>{base_url}/site/{kb_name}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>")

        # Entry pages
        for html_file in sorted(kb_dir.glob("*.html")):
            if html_file.name == "index.html":
                continue
            entry_id = html_file.stem
            stat = html_file.stat()
            lastmod = datetime.fromtimestamp(stat.st_mtime, tz=UTC).strftime("%Y-%m-%d")
            urls.append(
                f"  <url>\n    <loc>{base_url}/site/{kb_name}/{entry_id}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>"
            )

    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{"".join(urls)}\n</urlset>'
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _serve_search_page(cache_dir: Path) -> HTMLResponse:
    """Serve a dedicated search page for the /site/search route."""
    from ..services.site_cache import _render_template
    try:
        html = _render_template(
            "search.html",
            title="Search — Pyrite Knowledge Base",
            description="Search across all knowledge bases",
            og_title="Search — Pyrite Knowledge Base",
            og_type="website",
            canonical='<link rel="canonical" href="/site/search">',
            extra_head='<meta name="robots" content="noindex">',
        )
    except Exception:
        # Fallback to legacy module
        from .static_search_page import SEARCH_PAGE_HTML
        html = SEARCH_PAGE_HTML
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _serve_site_cached(cache_dir: Path, path: str, fallback_html: str) -> HTMLResponse:
    """Serve a /site page from the cache directory.

    Cache layout:
        /site           → cache_dir/index.html
        /site/boyd      → cache_dir/boyd/index.html
        /site/boyd/ooda → cache_dir/boyd/ooda.html
    """
    if not path:
        cache_path = cache_dir / "index.html"
    else:
        parts = path.rstrip("/").split("/")
        if len(parts) == 1:
            cache_path = cache_dir / parts[0] / "index.html"
        else:
            cache_path = cache_dir / parts[0] / ("/".join(parts[1:]) + ".html")

    # Security: ensure resolved path is within cache_dir
    try:
        resolved = cache_path.resolve()
        if not resolved.is_relative_to(cache_dir.resolve()):
            return HTMLResponse(status_code=404)
    except (ValueError, OSError):
        return HTMLResponse(status_code=404)

    if cache_path.is_file():
        return HTMLResponse(
            content=cache_path.read_text(encoding="utf-8"),
            headers={
                "Cache-Control": "public, max-age=3600, s-maxage=86400",
                "X-Pyrite-Cache": "HIT",
            },
        )

    # Cache miss — return SPA fallback (client-side rendering)
    return HTMLResponse(
        content=fallback_html,
        headers={"X-Pyrite-Cache": "MISS"},
    )
