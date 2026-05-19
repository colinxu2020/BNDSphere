FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/.uv-cache

RUN groupadd -r appuser -g 1000 && \
    useradd -r -g appuser -u 1000 -m -s /usr/sbin/nologin appuser
WORKDIR /backend
RUN chown appuser:appuser /backend
USER appuser:appuser
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1


FROM base AS dev
RUN uv sync --frozen --no-cache
ENV DEBUG=true
CMD ["/backend/.venv/bin/fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS prod
RUN uv sync --frozen --no-dev --no-cache
COPY --chown=appuser:appuser . .
ENV DEBUG=false
CMD ["/backend/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
