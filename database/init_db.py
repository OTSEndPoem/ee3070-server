"""
数据库初始化脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine
from database.models import Base, Product, Coupon
from sqlalchemy.orm import sessionmaker
import csv
import os

# 创建会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库：创建所有表"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully!")


def load_products_from_csv(csv_path: str):
    """从 CSV 导入商品数据"""
    if not os.path.exists(csv_path):
        print(f"⚠️  CSV file not found: {csv_path}")
        return

    db = SessionLocal()
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                try:
                    # 获取必要字段
                    sku = int(row.get("SKU", 0))
                    name = row.get("Name", row.get("name", "Unknown"))
                    price = float(row.get("Price", 0))
                    discount = float(row.get("Discount", 1.0))
                    
                    if sku <= 0:
                        continue
                    
                    # 检查是否已存在
                    existing = db.query(Product).filter(Product.sku == sku).first()
                    if existing:
                        print(f"  SKU {sku} already exists, skipping...")
                        continue
                    
                    product = Product(
                        sku=sku,
                        name=name,
                        price=price,
                        discount=discount
                    )
                    db.add(product)
                    count += 1
                except (ValueError, KeyError) as e:
                    print(f"  ⚠️  Error parsing row: {row} - {e}")
                    continue
            
            db.commit()
            print(f"✓ Loaded {count} products from {csv_path}")
    except Exception as e:
        print(f"✗ Error loading products: {e}")
        db.rollback()
    finally:
        db.close()


def load_coupons_from_csv(csv_path: str):
    """从 CSV 导入优惠券数据"""
    if not os.path.exists(csv_path):
        print(f"⚠️  CSV file not found: {csv_path}")
        return

    db = SessionLocal()
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                try:
                    code = row.get("Code", row.get("code", "")).strip()
                    discount_rate = float(row.get("DiscountRate", row.get("discount_rate", 1.0)))
                    valid = int(row.get("Valid", row.get("valid", 1)))
                    
                    if not code:
                        continue
                    
                    # 检查是否已存在
                    existing = db.query(Coupon).filter(Coupon.code == code).first()
                    if existing:
                        continue
                    
                    coupon = Coupon(
                        code=code,
                        discount_rate=discount_rate,
                        valid=valid
                    )
                    db.add(coupon)
                    count += 1
                except (ValueError, KeyError) as e:
                    print(f"  ⚠️  Error parsing row: {row} - {e}")
                    continue
            
            db.commit()
            print(f"✓ Loaded {count} coupons from {csv_path}")
    except Exception as e:
        print(f"✗ Error loading coupons: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    
    # 尝试从 EE3070 根目录加载 CSV 数据
    base_path = Path(__file__).resolve().parent.parent.parent
    dataset_csv = base_path / "dataset.csv"
    coupon_csv = base_path / "coupon_state.csv"
    
    print(f"\nSearching for CSV files in: {base_path}")
    if dataset_csv.exists():
        load_products_from_csv(str(dataset_csv))
    if coupon_csv.exists():
        load_coupons_from_csv(str(coupon_csv))
    
    print("\n✓ Database initialization complete!")
