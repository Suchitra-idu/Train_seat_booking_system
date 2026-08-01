# Backend image. Build context is the repo root (pyproject/uv.lock live there).
# `config/` carries the timetable the seed step expands into dated trips (D22).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

WORKDIR /app

# Dependency layer, cached until pyproject/lock change.
COPY pyproject.toml ./
COPY uv.lock* ./
RUN uv sync --no-dev || uv sync

COPY alembic.ini ./
COPY config/ ./config/
COPY backend/ ./backend/

EXPOSE 8000
# compose overrides this per service (migrate/seed/api); the default runs the API.
CMD ["uv", "run", "--no-dev", "uvicorn", "slr.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
