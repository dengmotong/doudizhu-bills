import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent

# 数据库路径
DB_PATH = BASE_DIR / "data" / "bills.db"

# OpenAI 兼容 API 配置（Mimo 等）
# API Key：环境变量 OPENAI_API_KEY 或在页面中输入
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
# Base URL：环境变量 OPENAI_BASE_URL 或在页面中输入
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.xiaomimimo.com/v1")
# 模型名：环境变量 OPENAI_MODEL，默认 mimo-v2-omni
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "mimo-v2-omni")
