"""
Static file serving for the Pyrite web application.

Serves the built SvelteKit app from web/dist/ with SPA fallback:
- /site/* → pre-rendered static HTML from site-cache/ (SEO-friendly)
- /assets/* → static files (JS, CSS, images)
- /api/* → handled by API router (not intercepted here)
- Everything else → index.html (SPA client-side routing)
"""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles


def mount_static(app: FastAPI, dist_dir: Path) -> None:
    """Mount static file serving with SPA fallback.

    Args:
        app: The FastAPI application instance.
        dist_dir: Path to web/dist/ directory containing built SvelteKit output.
    """
    index_html = dist_dir / "index.html"
    if not index_html.exists():
        return

    # Cache the index.html content for SPA fallback
    index_content = index_html.read_text()

    # Resolve site cache directory
    data_dir = Path(os.environ.get("PYRITE_DATA_DIR", "."))
    site_cache_dir = data_dir / "site-cache"

    # Mount the assets directory for hashed static files
    assets_dir = dist_dir / "_app"
    if assets_dir.is_dir():
        app.mount("/_app", StaticFiles(directory=str(assets_dir)), name="svelte-app")

    # Also mount any top-level static assets (favicon, etc.)
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        favicon_path = dist_dir / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(str(favicon_path))
        return HTMLResponse(status_code=404)

    # Serve /site/* from pre-rendered cache
    @app.get("/site/{path:path}", include_in_schema=False)
    async def site_page(request: Request, path: str):
        return _serve_site_cached(site_cache_dir, path, index_content)

    @app.get("/site", include_in_schema=False)
    async def site_index(request: Request):
        return _serve_site_cached(site_cache_dir, "", index_content)

    # SPA fallback — catch all non-API routes and serve index.html
    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(request: Request, path: str):
        # Don't intercept API, docs, or health routes
        if path.startswith(("api/", "docs", "redoc", "openapi.json", "health", "auth/")):
            return HTMLResponse(status_code=404)

        # Check if it's a real static file in dist/
        file_path = dist_dir / path
        if file_path.is_file() and file_path.resolve().is_relative_to(dist_dir.resolve()):
            return FileResponse(str(file_path))

        # SPA fallback: serve index.html for client-side routing
        return HTMLResponse(content=index_content)


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
