# Backend image. Build context is the repo root (pyproject/uv.lock live there).
# P0: the app layer (L4) does not exist yet, so CMD is a placeholder health server;
# it becomes `uvicorn slr.app.main:app` in P5.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

WORKDIR /app

# Dependency layer — cached until pyproject/lock change.
COPY pyproject.toml ./
COPY uv.lock* ./
RUN uv sync --no-dev || uv sync

COPY backend/ ./backend/

EXPOSE 8000
# Placeholder until P5 wires FastAPI (which will run `uv run --no-dev uvicorn …`).
# Plain system python needs no venv sync, so it serves 200 on / immediately.
CMD ["python", "-m", "http.server", "8000"]
