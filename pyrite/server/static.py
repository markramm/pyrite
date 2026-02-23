"""
Static file serving for the Pyrite web application.

Serves the built SvelteKit app from web/dist/ with SPA fallback:
- /assets/* → static files (JS, CSS, images)
- /api/* → handled by API router (not intercepted here)
- Everything else → index.html (SPA client-side routing)
"""

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

    # Mount the assets directory for hashed static files
    assets_dir = dist_dir / "_app"
    if assets_dir.is_dir():
        app.mount("/_app", StaticFiles(directory=str(assets_dir)), name="svelte-app")

    # Also mount any top-level static assets (favicon, etc.)
    # These come from SvelteKit's static/ directory
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        favicon_path = dist_dir / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(str(favicon_path))
        return HTMLResponse(status_code=404)

    # SPA fallback — catch all non-API routes and serve index.html
    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(request: Request, path: str):
        # Don't intercept API, docs, or health routes
        if path.startswith(("api/", "docs", "redoc", "openapi.json", "health")):
            return HTMLResponse(status_code=404)

        # Check if it's a real static file in dist/
        file_path = dist_dir / path
        if file_path.is_file() and file_path.resolve().is_relative_to(dist_dir.resolve()):
            return FileResponse(str(file_path))

        # SPA fallback: serve index.html for client-side routing
        return HTMLResponse(content=index_content)
