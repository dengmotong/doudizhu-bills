# ---- Stage 1: 构建 Vue 前端 ----
FROM node:22-alpine AS frontend
WORKDIR /app/frontend

# 先复制依赖清单，利用 Docker 缓存
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python 后端 + 静态资源 ----
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 先复制依赖定义，利用 Docker 缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev && uv cache clean && rm -rf /root/.cache/uv

# 复制后端代码与前端构建产物
COPY backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./frontend/dist

# 数据目录
RUN mkdir -p data/images

EXPOSE 8000

# FastAPI 同时服务 /api 接口与前端静态资源
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
