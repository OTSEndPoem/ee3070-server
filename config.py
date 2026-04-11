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
WRITE_API_KEY = os.getenv("WRITE_API_KEY", "EE3070_WRITE_KEY")
READ_API_KEY = os.getenv("READ_API_KEY", "EE3070_READ_KEY")

# 应用配置
APP_NAME = "EE3070 Event Server"
APP_VERSION = "2.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# 事件写入重试节流，避免客户端疯狂重试把数据库打爆
MIN_EVENT_RETRY_INTERVAL = 0.25

# 创建数据目录
os.makedirs(f"{BASE_DIR}/data", exist_ok=True)
