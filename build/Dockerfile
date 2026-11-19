FROM ghcr.io/astral-sh/uv:0.13.9 AS uv
FROM python:3.12-slim AS python-base

FROM python-base AS dependencies
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-python-downloads

FROM python-base AS runtime
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=dependencies /app/.venv .venv
COPY app/ app/
COPY alembic.ini ./
COPY alembic/ alembic/

USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
