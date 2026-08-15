FROM python:3.11-slim

RUN pip install --no-cache-dir uv==0.9.11 \
    && groupadd --system gravewright \
    && useradd --system --gid gravewright --create-home gravewright

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY --chown=gravewright:gravewright . .
RUN uv sync --frozen --no-dev \
    && mkdir -p storage data \
    && chown -R gravewright:gravewright /app

ENV APP_ENV=development \
    APP_DEBUG=false \
    SESSION_COOKIE_NAME=gravewright_session \
    SESSION_MAX_AGE=86400 \
    DEFAULT_LOCALE=en \
    PRIVACY_ENABLED=false

EXPOSE 8000

USER gravewright

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${WEB_WORKERS:-1}"]
