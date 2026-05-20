# syntax=docker/dockerfile:1.7
FROM python:3.12-slim-bookworm

WORKDIR /workspace

ENV PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=7860 \
    ACCOUNTS_FILE=/workspace/data/accounts.json \
    USERS_FILE=/workspace/data/users.json \
    CAPTURES_FILE=/workspace/data/captures.json \
    PYTHONPATH=/workspace

ARG INSTALL_CJK_FONTS=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        fonts-liberation \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcups2 \
        libdbus-1-3 \
        libdbus-glib-1-2 \
        libdrm2 \
        libgbm1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpangocairo-1.0-0 \
        libpulse0 \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        libxshmfence1 \
    && if [ "$INSTALL_CJK_FONTS" = "true" ]; then apt-get install -y --no-install-recommends fonts-noto-cjk; fi \
    && mkdir -p /workspace/data /workspace/logs \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY backend/requirements.txt ./backend/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-compile -r backend/requirements.txt \
    && python -m playwright install --only-shell chromium \
    && rm -rf /tmp/* /var/tmp/*

COPY backend/ ./backend/
COPY statics/ ./statics/

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.getenv('PORT', '7860'), timeout=5).read()"

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
