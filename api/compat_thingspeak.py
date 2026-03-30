"""
ThingSpeak 兼容层 API
为 Arduino、Python GUI、MATLAB 提供兼容的接口
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from database import get_db
from database.models import Feed, Product
from config import THINGSPEAK_CHANNEL_ID, API_KEY, READ_API_KEY, MIN_UPDATE_INTERVAL
import json

router = APIRouter(prefix="/api/thingspeak", tags=["ThingSpeak Compatibility"])

# 追踪最后更新时间，用于防限频
last_update_time = {}


@router.post("/update")
async def update_feed(
    api_key: str = Query(..., description="API Key（兼容 ThingSpeak）"),
    field1: int = Query(None),
    field2: str = Query(None),
    field3: float = Query(None),
    field4: float = Query(None),
    field5: int = Query(None),
    field6: int = Query(None),
    field7: int = Query(None),
    field8: int = Query(None),
    db: Session = Depends(get_db)
):
    """
    上传数据到数据库
    兼容 ThingSpeak /update 端点
    
    ### 举例：
    ```
    POST /api/thingspeak/update?api_key=YXCJIC121UFP1I5G&field1=10000001&field3=9.99&field4=0.8&field5=3
    ```
    
    ### 返回：
    ```json
    {
        "entry_id": 123,
        "message": "Success"
    }
    ```
    """
    
    # 验证 API Key
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    # 防限频检查
    key = f"update_{api_key}"
    if key in last_update_time:
        elapsed = (datetime.utcnow() - last_update_time[key]).total_seconds()
        if elapsed < MIN_UPDATE_INTERVAL:
            return {
                "entry_id": None,
                "message": "Too many requests"
            }
    
    # 创建新的 Feed 记录
    try:
        feed = Feed(
            field1=field1,
            field2=field2,
            field3=field3,
            field4=field4,
            field5=field5,
            field6=field6,
            field7=field7,
            field8=field8,
            created_at=datetime.utcnow()
        )
        db.add(feed)
        db.commit()
        db.refresh(feed)
        
        # 更新最后更新时间
        last_update_time[key] = datetime.utcnow()
        
        return {
            "entry_id": feed.id,
            "message": "Success"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels/{channel_id}/feeds/last.json")
async def get_last_feed(
    channel_id: int,
    api_key: str = Query(..., alias="api_key"),
    db: Session = Depends(get_db)
):
    """
    获取最新的标签同步数据
    兼容 Arduino 的轮询请求
    
    ### 举例：
    ```
    GET /api/thingspeak/channels/3275131/feeds/last.json?api_key=63UFGEON1MVYP3Z6
    ```
    
    ### 返回：
    ```json
    {
        "channel": {"id": 3275131},
        "feed": {
            "id": 123,
            "created_at": "2024-01-15T10:30:00Z",
            "field1": 10000001,
            "field3": 9.99,
            "field4": 0.8,
            "field5": 3
        }
    }
    ```
    """
    
    # 验证频道 ID 和 API Key
    if channel_id != THINGSPEAK_CHANNEL_ID:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if api_key != READ_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        # 获取最新的标签同步记录 (msgType=3)
        latest = db.query(Feed).filter(
            Feed.field5 == 3  # LABEL_SYNC
        ).order_by(desc(Feed.created_at)).first()
        
        if not latest:
            return {
                "channel": {"id": channel_id},
                "feed": None
            }
        
        return {
            "channel": {"id": channel_id},
            "feed": {
                "id": latest.id,
                "created_at": latest.created_at.isoformat() + "Z" if latest.created_at else None,
                "field1": latest.field1,
                "field3": latest.field3,
                "field4": latest.field4,
                "field5": latest.field5,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels/{channel_id}/feeds.json")
async def get_feeds(
    channel_id: int,
    api_key: str = Query(..., alias="api_key"),
    results: int = Query(10, description="返回记录数，默认 10"),
    db: Session = Depends(get_db)
):
    """
    获取购物车数据（最近 N 条记录）
    兼容 MATLAB 的轮询请求
    
    ### 举例：
    ```
    GET /api/thingspeak/channels/3275131/feeds.json?api_key=63UFGEON1MVYP3Z6&results=10
    ```
    
    ### 返回：
    ```json
    {
        "channel": {"id": 3275131},
        "feeds": [
            {
                "id": 123,
                "created_at": "2024-01-15T10:30:00Z",
                "field1": 10000001,
                "field3": 9.99,
                "field4": 0.8,
                "field5": 2,
                "field6": 1,
                "field7": 1,
                "field8": 5
            }
        ]
    }
    ```
    """
    
    # 验证频道 ID 和 API Key
    if channel_id != THINGSPEAK_CHANNEL_ID:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if api_key != READ_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        # 限制结果数量
        results = min(max(results, 1), 1000)
        
        # 获取最新的 CART_SYNC 记录 (msgType=2)
        feeds_list = db.query(Feed).filter(
            Feed.field5 == 2  # CART_SYNC
        ).order_by(desc(Feed.created_at)).limit(results).all()
        
        return {
            "channel": {"id": channel_id},
            "feeds": [
                {
                    "id": feed.id,
                    "created_at": feed.created_at.isoformat() + "Z" if feed.created_at else None,
                    "field1": feed.field1,
                    "field3": feed.field3,
                    "field4": feed.field4,
                    "field5": feed.field5,
                    "field6": feed.field6,
                    "field7": feed.field7,
                    "field8": feed.field8,
                }
                for feed in feeds_list
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels/{channel_id}/fields/{field_id}.json")
async def get_field_data(
    channel_id: int,
    field_id: int,
    api_key: str = Query(..., alias="api_key"),
    results: int = Query(10),
    db: Session = Depends(get_db)
):
    """
    获取特定字段的历史数据
    兼容 ThingSpeak 字段查询
    """
    
    if channel_id != THINGSPEAK_CHANNEL_ID:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if api_key != READ_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        results = min(max(results, 1), 1000)
        
        feeds_list = db.query(Feed).order_by(
            desc(Feed.created_at)
        ).limit(results).all()
        
        # 根据 field_id 提取数据
        field_map = {
            1: "field1", 2: "field2", 3: "field3", 4: "field4",
            5: "field5", 6: "field6", 7: "field7", 8: "field8",
        }
        
        field_name = field_map.get(field_id)
        if not field_name:
            raise HTTPException(status_code=400, detail="Invalid field ID")
        
        return {
            "channel": {"id": channel_id},
            "field": field_id,
            "feeds": [
                {
                    "id": feed.id,
                    "created_at": feed.created_at.isoformat() + "Z" if feed.created_at else None,
                    "value": getattr(feed, field_name),
                }
                for feed in feeds_list
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
