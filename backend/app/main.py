"""FastAPI application entry point.

Wires up CORS and registers the feature routers. The database schema is managed
by Alembic migrations (`alembic upgrade head`), not created on startup.
"""

import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text
from starlette.staticfiles import StaticFiles

from app.api import analytics, anomalies, auth, query, subscriptions, transactions, upload
from app.core.config import settings
from app.core.database import engine
from app.core.logging import configure_logging, get_logger
from app.core.metrics import metrics
from app.services.categorizer import model_info

# Built React app, copied here in the Docker image (single-service deploy).
# Absent in local dev / tests, where the Vite dev server serves the frontend.
STATIC_DIR = Path(__file__).parent / "static"

configure_logging()
logger = get_logger("app.request")

app = FastAPI(title="JoMoney API")

# Compress large JSON payloads (e.g. /api/transactions) over ~500 bytes.
app.add_middleware(GZipMiddleware, minimum_size=500)

# Allow the React dev server to call this API from a different origin (port).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Tag each request with an id, time it, and log metadata (no payloads)."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    metrics.incr("http_requests_total")
    metrics.observe_ms("http_request", duration_ms)
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,  # path only — never query/body (financial data)
            "status": response.status_code,
            "duration_ms": round(duration_ms, 1),
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/api/health")
def health_check():
    """Liveness probe: checks DB connectivity and reports the loaded model."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.exception("health db check failed")
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "categorizer": model_info(),
    }


@app.get("/api/metrics")
def metrics_summary():
    """Aggregate counters + latencies (in-memory; resets on restart)."""
    return metrics.snapshot()


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
