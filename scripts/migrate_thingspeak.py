"""
从 ThingSpeak 迁移数据到本地数据库
"""
import sys
from pathlib import Path
import requests
from datetime import datetime
from sqlalchemy.orm import sessionmaker

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine
from database.models import Feed

# ThingSpeak 配置
THINGSPEAK_CHANNEL_ID = 3275131
READ_API_KEY = "63UFGEON1MVYP3Z6"
THINGSPEAK_API_URL = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/feeds.json"

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def migrate_from_thingspeak(results: int = 8000):
    """
    从 ThingSpeak 导出全部历史数据到本地数据库
    
    :param results: 要导出的记录数（最多 8000）
    """
    print(f"Starting migration from ThingSpeak (Channel {THINGSPEAK_CHANNEL_ID})...")
    
    db = SessionLocal()
    try:
        # 检查已有数据
        existing_count = db.query(Feed).count()
        if existing_count > 0:
            print(f"⚠️  Database already contains {existing_count} records.")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                return
        
        # 从 ThingSpeak 获取数据
        print(f"Fetching {results} records from ThingSpeak...")
        
        params = {
            'api_key': READ_API_KEY,
            'results': results,
        }
        
        response = requests.get(THINGSPEAK_API_URL, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        feeds = data.get('feeds', [])
        
        print(f"✓ Retrieved {len(feeds)} records from ThingSpeak")
        
        # 解析并插入数据库
        imported = 0
        failed = 0
        
        for feed_data in feeds:
            try:
                feed = Feed(
                    entry_id=feed_data.get('id'),
                    created_at=datetime.fromisoformat(
                        feed_data.get('created_at', '').replace('Z', '+00:00')
                    ) if feed_data.get('created_at') else datetime.utcnow(),
                    field1=int(feed_data['field1']) if feed_data.get('field1') else None,
                    field2=feed_data.get('field2'),
                    field3=float(feed_data['field3']) if feed_data.get('field3') else None,
                    field4=float(feed_data['field4']) if feed_data.get('field4') else None,
                    field5=int(feed_data['field5']) if feed_data.get('field5') else None,
                    field6=int(feed_data['field6']) if feed_data.get('field6') else None,
                    field7=int(feed_data['field7']) if feed_data.get('field7') else None,
                    field8=int(feed_data['field8']) if feed_data.get('field8') else None,
                )
                db.add(feed)
                imported += 1
                
                if imported % 100 == 0:
                    print(f"  ...imported {imported} records...")
                    
            except Exception as e:
                print(f"  ⚠️  Error parsing feed {feed_data.get('id')}: {e}")
                failed += 1
                continue
        
        # 提交到数据库
        db.commit()
        print(f"✓ Successfully imported {imported} records (failed: {failed})")
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching from ThingSpeak: {e}")
    except Exception as e:
        print(f"✗ Migration error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate data from ThingSpeak to local database")
    parser.add_argument("--results", type=int, default=8000, help="Number of records to import (max 8000)")
    args = parser.parse_args()
    
    migrate_from_thingspeak(results=args.results)
