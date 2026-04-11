"""
数据库模型定义
"""
import json
from sqlalchemy import Column, Integer, Float, String, DateTime, Index, Text
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


class EventLog(Base):
    """
    统一事件日志表
    """
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    event_type = Column(String(64), nullable=False)
    command_group = Column(String(64), nullable=True)
    device_id = Column(String(64), nullable=True)
    peer_device_id = Column(String(64), nullable=True)
    entity_type = Column(String(32), nullable=True)
    entity_id = Column(String(64), nullable=True)

    sku = Column(Integer, nullable=True)
    name = Column(String(255), nullable=True)
    price = Column(Float, nullable=True)
    discount = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=True)
    coupon_code = Column(String(64), nullable=True)
    tx_id = Column(Integer, nullable=True)

    request_id = Column(String(64), nullable=True)
    trace_id = Column(String(64), nullable=True)
    status = Column(String(32), nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(String(1024), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    payload_json = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_event_type_timestamp', 'event_type', 'created_at'),
        Index('idx_device_timestamp', 'device_id', 'created_at'),
        Index('idx_trace_timestamp', 'trace_id', 'created_at'),
        Index('idx_tx_timestamp', 'tx_id', 'created_at'),
        Index('idx_coupon_timestamp', 'coupon_code', 'created_at'),
        Index('idx_entity_timestamp', 'entity_type', 'entity_id', 'created_at'),
    )

    def _decode_payload(self):
        if not self.payload_json:
            return {}
        try:
            return json.loads(self.payload_json)
        except Exception:
            return {"raw": self.payload_json}

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "event_type": self.event_type,
            "command_group": self.command_group,
            "device_id": self.device_id,
            "peer_device_id": self.peer_device_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "sku": self.sku,
            "name": self.name,
            "price": self.price,
            "discount": self.discount,
            "quantity": self.quantity,
            "coupon_code": self.coupon_code,
            "tx_id": self.tx_id,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "status": self.status,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "latency_ms": self.latency_ms,
            "payload": self._decode_payload(),
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
