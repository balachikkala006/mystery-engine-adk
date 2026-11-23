# Multi-stage production Dockerfile for the Interactive AI Mystery Engine (Google ADK)
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml requirements.txt README.md ./
COPY mystery_engine ./mystery_engine
RUN pip install --upgrade pip && pip install . "a2a-sdk>=0.3.0"


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HOST=0.0.0.0 \
    PORT=8080 \
    SESSION_BACKEND=sqlite \
    SESSION_DB_PATH=/app/data/sessions/mystery_sessions.db \
    LOG_FORMAT=json

RUN groupadd --gid 10001 appuser && \
    useradd --uid 10001 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser mystery_engine ./mystery_engine
COPY --chown=appuser:appuser evals ./evals
COPY --chown=appuser:appuser main.py pyproject.toml ./

RUN mkdir -p /app/data/sessions && chown -R appuser:appuser /app/data

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python main.py --health || exit 1

# Serves the ADK API / Web UI by default; override CMD for `--a2a` or CLI mode
CMD ["sh", "-c", "adk api_server --host 0.0.0.0 --port ${PORT:-8080} ."]
