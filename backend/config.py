"""全局配置 — 唯一配置来源。

路径、数据库、图片目录、OpenAI 兼容 API 配置均在此定义。
`.env` 使用 override=True，因此 `.env` 优先于系统环境变量。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（backend 的上一级）
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载 .env（override=True 确保 .env 优先于系统环境变量）
load_dotenv(BASE_DIR / ".env", override=True)

# 数据库路径
DB_PATH = BASE_DIR / "data" / "bills.db"

# 上传截图目录
IMAGES_DIR = BASE_DIR / "data" / "images"

# 前端构建产物目录
DIST_DIR = BASE_DIR / "frontend" / "dist"

# OpenAI 兼容 API 配置（Mimo 等）
# API Key：环境变量 OPENAI_API_KEY 或在页面中输入
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
# Base URL：环境变量 OPENAI_BASE_URL 或在页面中输入
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.xiaomimimo.com/v1")
# 模型名：环境变量 OPENAI_MODEL
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "mimo-v2.5")

# 确保目录存在
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
