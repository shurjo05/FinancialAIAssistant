# Single-service image: FastAPI serves the API and the built React app.
# Build context is the REPO ROOT (needs backend/, frontend/, and data/):
#   docker build -f backend/Dockerfile -t finance-ai .

# ---- Stage 1: build the React frontend ----
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build            # -> /frontend/dist

# ---- Stage 2: Python runtime (inference stack only, no training deps) ----
FROM python:3.11-slim AS backend
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app/backend

# Install deps first for layer caching (requirements.txt = runtime only).
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code, then bake in the pinned model from its GitHub Release.
COPY backend/ ./
RUN python -m scripts.fetch_model

# Preserve the repo layout so repo_root/data/*.csv resolves (parents[3] in
# upload.py), and drop the built frontend where main.py serves it.
WORKDIR /app
COPY data/ ./data/
COPY --from=frontend /frontend/dist ./backend/app/static

WORKDIR /app/backend
EXPOSE 8000
# Migrations are NOT run here (no DB at build time) — they run as a deploy-time
# step (compose command / Render release phase) before the app starts.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
