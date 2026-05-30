FROM python:3.13-slim

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 先复制依赖定义，利用 Docker 缓存
COPY pyproject.toml uv.lock ./

# 安装依赖并清理缓存
RUN uv sync --frozen --no-dev && uv cache clean && rm -rf /root/.cache/uv

# 复制项目代码
COPY . .

# 数据目录
RUN mkdir -p data/images

EXPOSE 8501

ENTRYPOINT ["uv", "run", "streamlit", "run", "app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--browser.gatherUsageStats=false"]
