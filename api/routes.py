"""
核心 REST API 路由
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from database import get_db
from database.models import Feed, Product, Coupon
from datetime import datetime, timedelta

router = APIRouter(prefix="/api", tags=["Core APIs"])


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/feeds")
async def list_feeds(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    msg_type: int = Query(None, description="消息类型筛选 (1-5)"),
    db: Session = Depends(get_db)
):
    """
    列出所有数据条目，支持筛选和分页
    
    ### 消息类型：
    - 1: ENTRY_INFO (录入事件)
    - 2: CART_SYNC (购物车扫描)
    - 3: LABEL_SYNC (标签同步)
    - 4: CHECKOUT_INFO (结账信息)
    - 5: PAYMENT_OK (付款成功)
    """
    try:
        query = db.query(Feed)
        
        if msg_type is not None:
            query = query.filter(Feed.field5 == msg_type)
        
        total = query.count()
        feeds = query.order_by(desc(Feed.created_at)).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "count": len(feeds),
            "offset": offset,
            "limit": limit,
            "feeds": [feed.to_dict() for feed in feeds]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feeds/{feed_id}")
async def get_feed(feed_id: int, db: Session = Depends(get_db)):
    """获取单条数据记录"""
    try:
        feed = db.query(Feed).filter(Feed.id == feed_id).first()
        if not feed:
            raise HTTPException(status_code=404, detail="Feed not found")
        return feed.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feeds")
async def create_feed(
    field1: int = None,
    field2: str = None,
    field3: float = None,
    field4: float = None,
    field5: int = None,
    field6: int = None,
    field7: int = None,
    field8: int = None,
    db: Session = Depends(get_db)
):
    """创建新的数据记录"""
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
        return feed.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products")
async def list_products(db: Session = Depends(get_db)):
    """列出所有商品"""
    try:
        products = db.query(Product).order_by(Product.sku).all()
        return {
            "count": len(products),
            "products": [p.to_dict() for p in products]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{sku}")
async def get_product(sku: int, db: Session = Depends(get_db)):
    """查询商品信息"""
    try:
        product = db.query(Product).filter(Product.sku == sku).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coupons")
async def list_coupons(
    valid_only: bool = Query(False, description="只列出有效优惠券"),
    db: Session = Depends(get_db)
):
    """列出优惠券"""
    try:
        query = db.query(Coupon)
        if valid_only:
            query = query.filter(Coupon.valid == 1)
        
        coupons = query.order_by(Coupon.code).all()
        return {
            "count": len(coupons),
            "coupons": [c.to_dict() for c in coupons]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_summary(
    time_range: str = Query("1h", description="时间范围: 1h, 24h, 7d, all"),
    db: Session = Depends(get_db)
):
    """
    获取统计信息
    
    ### 时间范围：
    - 1h: 最近 1 小时
    - 24h: 最近 24 小时
    - 7d: 最近 7 天
    - all: 全部数据
    """
    try:
        # 计算时间范围
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        else:
            start_time = datetime.min
        
        # 查询
        base_query = db.query(Feed).filter(Feed.created_at >= start_time)
        
        # 计算统计
        total_feeds = base_query.count()
        
        # 按消息类型统计
        msg_type_counts = {}
        for msg_type in range(1, 6):
            count = base_query.filter(Feed.field5 == msg_type).count()
            if count > 0:
                msg_type_counts[f"msgType_{msg_type}"] = count
        
        # 计算购物车总额
        cart_feeds = base_query.filter(Feed.field5 == 2)  # CART_SYNC
        total_amount = db.session.query(
            func.sum(Feed.field3 * Feed.field8 * Feed.field4)
        ).filter(Feed.created_at >= start_time, Feed.field5 == 2).scalar() or 0.0
        
        # 统计商品数量
        total_qty = db.session.query(
            func.sum(Feed.field8)
        ).filter(Feed.created_at >= start_time, Feed.field5 == 2).scalar() or 0
        
        return {
            "time_range": time_range,
            "start_time": start_time.isoformat(),
            "end_time": now.isoformat(),
            "total_feeds": total_feeds,
            "message_types": msg_type_counts,
            "cart_summary": {
                "total_amount": float(total_amount),
                "total_quantity": int(total_qty),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
