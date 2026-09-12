# TuViMCP FastAPI — Cloud Run / local Docker
FROM python:3.12-slim

WORKDIR /app

# System deps for Pillow (often needed on slim)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Install package with API extras only (no .env baked in)
COPY pyproject.toml README.md ./
COPY tuvi_mcp ./tuvi_mcp
RUN pip install --no-cache-dir -e ".[api]"

# Non-root runtime
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
EXPOSE 8080

# Cloud Run injects PORT; sh -c expands it and forwards signals
CMD ["sh", "-c", "uvicorn tuvi_mcp.api.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
