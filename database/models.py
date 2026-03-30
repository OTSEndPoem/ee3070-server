"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Feed(Base):
    """
    主数据表 - 替代 ThingSpeak 的数据存储
    映射 ThingSpeak 8 个字段
    """
    __tablename__ = "feeds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # ThingSpeak 字段映射
    field1 = Column(Integer, nullable=True)  # SKU
    field2 = Column(String(255), nullable=True)  # 商品名称（可选，从 dataset.csv 查询）
    field3 = Column(Float, nullable=True)  # 单价 (Price)
    field4 = Column(Float, nullable=True)  # 打折系数 (Discount)
    field5 = Column(Integer, nullable=True)  # 交易类型 (MsgType: 1=ENTRY_INFO, 2=CART_SYNC, 3=LABEL_SYNC, 4=CHECKOUT_INFO, 5=PAYMENT_OK)
    field6 = Column(Integer, nullable=True)  # 扫描次数 (ScanCount)
    field7 = Column(Integer, nullable=True)  # 交易ID (TxID)
    field8 = Column(Integer, nullable=True)  # 数量 (Qty)
    
    # 便捷字段
    entry_id = Column(Integer, nullable=True)  # ThingSpeak 兼容的 entry ID
    
    # 索引：加速按 msgType 和时间戳查询
    __table_args__ = (
        Index('idx_msgtype_timestamp', 'field5', 'created_at'),
        Index('idx_timestamp', 'created_at'),
        Index('idx_field1_timestamp', 'field1', 'created_at'),
    )

    def __repr__(self):
        return f"<Feed id={self.id} field5={self.field5} created_at={self.created_at}>"

    def to_dict(self):
        """转换为字典，用于 JSON 响应"""
        return {
            "entry_id": self.entry_id or self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "field1": self.field1,
            "field2": self.field2,
            "field3": self.field3,
            "field4": self.field4,
            "field5": self.field5,
            "field6": self.field6,
            "field7": self.field7,
            "field8": self.field8,
        }

    def to_thingspeak_dict(self):
        """转换为 ThingSpeak 格式的字典"""
        return {
            "entry_id": self.entry_id or self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "field1": self.field1,
            "field3": self.field3,
            "field4": self.field4,
            "field5": self.field5,
            "field6": self.field6,
            "field7": self.field7,
            "field8": self.field8,
        }


class Product(Base):
    """
    商品信息表 - 从 dataset.csv 导入
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(Integer, unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    discount = Column(Float, default=1.0, nullable=False)  # 打折系数
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_sku', 'sku'),
    )

    def __repr__(self):
        return f"<Product sku={self.sku} name={self.name}>"

    def to_dict(self):
        return {
            "sku": self.sku,
            "name": self.name,
            "price": self.price,
            "discount": self.discount,
        }


class Coupon(Base):
    """
    优惠券表 - 从 coupon_state.csv 导入
    """
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    discount_rate = Column(Float, nullable=False)  # 折扣率 (0-1, 1=100% 对应无折扣)
    valid = Column(Integer, default=1, nullable=False)  # 1=有效, 0=无效
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_code', 'code'),
    )

    def __repr__(self):
        return f"<Coupon code={self.code} discount_rate={self.discount_rate}>"

    def to_dict(self):
        return {
            "code": self.code,
            "discount_rate": self.discount_rate,
            "valid": self.valid,
        }
