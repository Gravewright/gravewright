FROM python:3.11-slim

RUN pip install uv --no-cache-dir

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

RUN mkdir -p storage

ENV APP_ENV=development \
    APP_DEBUG=false \
    SESSION_SECRET=perf-test-secret-key-change-me \
    SESSION_COOKIE_NAME=gravewright_session \
    SESSION_MAX_AGE=86400 \
    DEFAULT_LOCALE=en \
    PRIVACY_ENABLED=false

EXPOSE 8000




CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${WEB_WORKERS:-1}"]
