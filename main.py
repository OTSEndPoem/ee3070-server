"""
FastAPI 主应用
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from config import APP_NAME, APP_VERSION, DEBUG
from database import engine
from database.models import Base
from api import compat_thingspeak, routes

# 创建表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="ThingSpeak 替代方案 - 面向 Arduino、Python GUI、MATLAB 和 OpenClaw AI 的数据存储与查询服务",
    debug=DEBUG
)

# CORS 配置（允许所有来源，生产环境应限制）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(compat_thingspeak.router)
app.include_router(routes.router)


@app.get("/")
async def root():
    """
    根端点 - 欢迎信息
    """
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "docs": "http://localhost:8000/docs",
        "redoc": "http://localhost:8000/redoc",
        "message": "EE3070 Server is running!",
        "endpoints": {
            "ThingSpeak Compatible": "/api/thingspeak/*",
            "Core APIs": "/api/*",
            "Health Check": "/api/health",
            "API Docs": "/docs",
        }
    }


@app.get("/info")
async def get_info():
    """获取服务器信息"""
    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "debug": DEBUG,
        "database": "SQLite (local)",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
        log_level="info"
    )
