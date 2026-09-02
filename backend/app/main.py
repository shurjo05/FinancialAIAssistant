"""FastAPI application entry point.

Wires up CORS and registers the feature routers. The database schema is managed
by Alembic migrations (`alembic upgrade head`), not created on startup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, anomalies, auth, query, subscriptions, transactions, upload
from app.core.config import settings
from app.services.categorizer import model_info

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


# Feature routers.
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(transactions.router)
app.include_router(subscriptions.router)
app.include_router(anomalies.router)
app.include_router(query.router)
app.include_router(analytics.router)
