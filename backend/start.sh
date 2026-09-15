#!/bin/sh
# Container entrypoint: apply DB migrations, then start the server.
# Kept as a script (not an inline command) so shell operators like && aren't at
# the mercy of how the platform tokenizes a command string. PORT is provided by
# the host (Render sets it); defaults to 8000 locally.
set -e

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
