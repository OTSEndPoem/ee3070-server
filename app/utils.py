"""
依赖项和工具函数
"""
from datetime import datetime
from sqlalchemy.orm import Session


def get_current_timestamp() -> str:
    """获取当前 ISO 格式时间戳"""
    return datetime.utcnow().isoformat() + "Z"


def get_sku_from_field1(field1: int) -> int:
    """从 field1 提取 SKU"""
    return field1 if field1 else None


def calculate_total_price(price: float, discount: float, qty: int) -> float:
    """计算总价格"""
    if not all([price, discount, qty]):
        return 0.0
    return price * discount * qty
