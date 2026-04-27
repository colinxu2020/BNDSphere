FROM python:3.14-slim

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

RUN uv sync --frozen --no-dev --no-cache

COPY --chown=appuser:appuser . .

EXPOSE 8000

CMD ["/backend/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
