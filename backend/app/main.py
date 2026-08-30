"""FastAPI application entry point.

Wires up CORS, creates database tables on startup, and exposes a health
check. Feature routers (upload, transactions, analytics, ...) are registered
here as they are built.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, anomalies, query, subscriptions, transactions, upload
from app.core.config import settings
from app.core.database import Base, engine

# Importing the models module registers every table on Base.metadata so that
# create_all() below knows what to create. Without this import, no tables exist.
from app.models import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once on startup: create any tables that don't exist yet.
    # (create_all is a no-op for tables that are already present.)
    Base.metadata.create_all(bind=engine)
    yield
    # Nothing to clean up on shutdown for now.


app = FastAPI(title="Personal Finance AI Assistant", lifespan=lifespan)

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
    """Simple liveness probe used to confirm the API is running."""
    return {"status": "ok"}


# Feature routers.
app.include_router(upload.router)
app.include_router(transactions.router)
app.include_router(subscriptions.router)
app.include_router(anomalies.router)
app.include_router(query.router)
app.include_router(analytics.router)
