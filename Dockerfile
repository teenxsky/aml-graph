ARG PYTHON_VERSION=3.14.3
ARG NODE_VERSION=24.15.0


# ========================= Python App (BASE) =========================
FROM python:${PYTHON_VERSION}-slim AS base-backend
WORKDIR /app

# Python / PIP
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Установка uv
RUN pip install --no-cache-dir uv


# ========================= Python App (backend) =========================
FROM base-backend AS backend
WORKDIR /app

# Копируем только зависимости (для кеша слоёв)
COPY backend/pyproject.toml \
     backend/uv.lock \
     ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Копируем код
COPY ./backend .

# Устанавливаем сам проект
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

ENTRYPOINT ["uv", "run", "python", "-m", "src.main"]


# ========================= Python App (task worker) =========================
FROM backend AS task-worker
WORKDIR /app

ENTRYPOINT ["uv", "run", "taskiq", "worker", "src.task_worker:broker", "-r", "--workers", "4", "--max-threadpool-threads", "8", "--shutdown-timeout", "999999"]


# ========================= Frontend App =========================
FROM node:${NODE_VERSION}-slim AS frontend
WORKDIR /app

COPY frontend/package.json \
     frontend/package-lock.json \
     frontend/next.config.ts \
     frontend/tsconfig.json \
     frontend/postcss.config.mjs \
     frontend/.npmrc \
     frontend/.nvmrc \
     .env.example \
     ./

RUN npm ci

COPY ./frontend ./
