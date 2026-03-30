"""
配置文件 - 环境变量及数据库设置
"""
import os
from pathlib import Path

# 项目路径
BASE_DIR = Path(__file__).resolve().parent

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR}/data/ee3070.db"  # 默认 SQLite
)

# API 配置
API_KEY = os.getenv("API_KEY", "YXCJIC121UFP1I5G")  # ThingSpeak 兼容的 Write Key
READ_API_KEY = os.getenv("READ_API_KEY", "63UFGEON1MVYP3Z6")  # Read Key

# 应用配置
APP_NAME = "EE3070 Server"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# ThingSpeak 兼容配置
THINGSPEAK_CHANNEL_ID = 3275131  # 原始 Channel ID（用于兼容）
MIN_UPDATE_INTERVAL = 15.2  # 秒，防止限频

# 创建数据目录
os.makedirs(f"{BASE_DIR}/data", exist_ok=True)
