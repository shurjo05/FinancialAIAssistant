"""FastAPI application entry point.

Wires up CORS and registers the feature routers. The database schema is managed
by Alembic migrations (`alembic upgrade head`), not created on startup.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import analytics, anomalies, auth, query, subscriptions, transactions, upload
from app.core.config import settings
from app.services.categorizer import model_info

# Built React app, copied here in the Docker image (single-service deploy).
# Absent in local dev / tests, where the Vite dev server serves the frontend.
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Personal Finance AI Assistant")

# Allow the React dev server to call this API from a different origin (port).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    """Liveness probe; also reports which categorizer model is loaded."""
    return {"status": "ok", "categorizer": model_info()}


# Feature routers (registered before the SPA fallback so /api wins).
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(transactions.router)
app.include_router(subscriptions.router)
app.include_router(anomalies.router)
app.include_router(query.router)
app.include_router(analytics.router)


# Serve the built React app from the same origin (single-service deploy). Only
# active when the static bundle is present (i.e. inside the Docker image).
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve real static files; fall back to index.html for SPA routes.

        API routes are registered above and match first. Any unmatched /api path
        is a genuine 404 (not the SPA shell), so API 404s stay JSON.
        """
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
