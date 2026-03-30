# EE3070 Server - ThingSpeak 替代方案

一个 FastAPI Web 服务器，替代 ThingSpeak 为 Arduino、Python GUI、MATLAB 和 OpenClaw AI 提供数据存储和查询服务。

## 特性

- 🎯 **ThingSpeak 兼容**：Arduino、Python GUI、MATLAB 无需修改核心逻辑，仅改 API 端点即可
- 📊 **数据库存储**：使用 SQLite（默认）或 PostgreSQL，支持 CART、LABEL、PAYMENT 等多类交易数据
- 🔍 **丰富的查询 API**：支持购物车查询、商品列表、交易历史、统计摘要等
- 🤖 **MCP 集成**：通过 Model Context Protocol 为 OpenClaw AI 提供数据接口
- 🛡️ **API Key 验证**：兼容 ThingSpeak 的 API Key 机制
- 📈 **高性能索引**：数据库表配置了时间戳和消息类型索引，加速查询

## 快速开始

### 1. 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python database/init_db.py
```

这将：
- 创建 SQLite 数据库（`data/ee3070.db`）
- 创建必要的表（feeds、products、coupons）
- 从 `../dataset.csv` 导入商品数据
- 从 `../coupon_state.csv` 导入优惠券数据

### 3. 启动 Web 服务

```bash
python main.py
```

服务器将在 `http://localhost:8000` 启动，提供以下文档页面：
- API 文档：http://localhost:8000/docs (Swagger UI)
- ReDoc 文档：http://localhost:8000/redoc

## API 端点

### ThingSpeak 兼容端点

#### POST /api/thingspeak/update
上传数据（兼容 Arduino/Python/MATLAB）

```bash
curl -X POST "http://localhost:8000/api/thingspeak/update?api_key=YOUR_WRITE_API_KEY&field1=10000001&field3=9.99&field4=0.8&field5=3"
```

**响应：**
```json
{
  "entry_id": 123,
  "message": "Success"
}
```

#### GET /api/thingspeak/channels/{channel_id}/feeds/last.json
获取最新标签同步记录（Arduino 轮询）

```bash
curl "http://localhost:8000/api/thingspeak/channels/3275131/feeds/last.json?api_key=YOUR_READ_API_KEY"
```

**响应：**
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

#### GET /api/thingspeak/channels/{channel_id}/feeds.json
获取购物车数据（MATLAB 轮询）

```bash
curl "http://localhost:8000/api/thingspeak/channels/3275131/feeds.json?api_key=YOUR_READ_API_KEY&results=10"
```

### 核心 API 端点

#### GET /api/health
健康检查

```bash
curl http://localhost:8000/api/health
```

#### GET /api/feeds
列出所有数据条目

```bash
curl "http://localhost:8000/api/feeds?limit=100&offset=0&msg_type=2"
```

#### GET /api/products
查询商品列表

```bash
curl http://localhost:8000/api/products
```

#### GET /api/products/{sku}
查询单个商品

```bash
curl http://localhost:8000/api/products/10000001
```

#### GET /api/coupons
查询优惠券

```bash
curl http://localhost:8000/api/coupons?valid_only=true
```

#### GET /api/stats/summary
获取统计摘要

```bash
curl "http://localhost:8000/api/stats/summary?time_range=24h"
```

## 配置

编辑 [config.py](config.py) 修改配置：

```python
# 数据库 URL
DATABASE_URL = "sqlite:///data/ee3070.db"  # 或 "postgresql://user:pass@localhost/ee3070"

# API 密钥
API_KEY = "YOUR_WRITE_API_KEY"  # Write Key（兼容 ThingSpeak）
READ_API_KEY = "YOUR_READ_API_KEY"  # Read Key

# Channel ID（兼容 ThingSpeak）
THINGSPEAK_CHANNEL_ID = 3275131

# 防限频间隔（秒）
MIN_UPDATE_INTERVAL = 15.2
```

或通过环境变量：

```bash
export DATABASE_URL="sqlite:///data/ee3070.db"
export API_KEY="your-write-key"
export READ_API_KEY="your-read-key"
export DEBUG="True"
```

## 数据库架构

### feeds 表
主数据表，映射 ThingSpeak 的 8 个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER (PK) | 自增主键 |
| created_at | DATETIME | 创建时间戳 |
| field1 | INTEGER | SKU |
| field2 | STRING | 商品名称 |
| field3 | FLOAT | 单价 |
| field4 | FLOAT | 打折系数 |
| field5 | INTEGER | 消息类型（1-5） |
| field6 | INTEGER | 扫描次数 |
| field7 | INTEGER | 交易 ID |
| field8 | INTEGER | 数量 |

**消息类型 (field5)：**
- 1: ENTRY_INFO - 录入事件
- 2: CART_SYNC - 购物车扫描
- 3: LABEL_SYNC - 标签同步
- 4: CHECKOUT_INFO - 结账信息
- 5: PAYMENT_OK - 付款成功

### products 表
商品信息（从 dataset.csv 导入）

### coupons 表
优惠券信息（从 coupon_state.csv 导入）

## 迁移现有数据

从 ThingSpeak 导出历史数据到本地数据库：

```bash
python scripts/migrate_thingspeak.py --results 8000
```

## 修改本地客户端

### Arduino (arduino-code-merged.ino)

**修改前：**
```cpp
const char* THINGSPEAK_HOST = "api.thingspeak.com";
```

**修改后：**
```cpp
const char* THINGSPEAK_HOST = "your-server-ip";  // 腾讯云服务器 IP
const uint16_t THINGSPEAK_PORT = 8000;
```

### Python GUI (RFID-write/gui_merged.py)

**修改前：**
```python
THINGSPEAK_UPDATE_URL = "https://api.thingspeak.com/update"
```

**修改后：**
```python
THINGSPEAK_UPDATE_URL = "http://your-server-ip:8000/api/thingspeak/update"
```

### MATLAB (cart_exported.m)

**修改前：**
```matlab
channelID = 3275131;
url = "https://api.thingspeak.com/channels/" + string(channelID) + "/feeds.json";
```

**修改后：**
```matlab
url = "http://your-server-ip:8000/api/thingspeak/channels/3275131/feeds.json";
```

## 部署到腾讯云

### 1. SSH 到服务器

```bash
ssh root@your-server-ip
```

### 2. 克隆仓库

```bash
cd /opt
git clone https://github.com/your-username/ee3070-server.git
cd ee3070-server
```

### 3. 安装依赖

```bash
python3 -m pip install -r requirements.txt
```

### 4. 初始化数据库

```bash
python3 database/init_db.py
```

### 5. 启动服务（使用 systemd）

创建 `/etc/systemd/system/ee3070-server.service`：

```ini
[Unit]
Description=EE3070 Web Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ee3070-server
ExecStart=/usr/bin/python3 /opt/ee3070-server/main.py
Restart=always
RestartSec=10
Environment="DEBUG=False"

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ee3070-server
sudo systemctl start ee3070-server
```

### 6. 配置防火墙

```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 8000/tcp  # Web 服务
sudo ufw enable
```

## 监控和日志

### 查看服务日志

```bash
sudo journalctl -u ee3070-server -f
```

### 健康检查

```bash
curl http://your-server-ip:8000/api/health
```

### 访问 API 文档

在浏览器中打开：
- http://your-server-ip:8000/docs (Swagger UI)
- http://your-server-ip:8000/redoc

## 性能优化

- **索引**：feeds 表已建立 msgType + timestamp 复合索引，加速常见查询
- **分页**：API 返回提供 offset/limit，支持大数据集查询
- **缓存**：可在 Nginx 或 Redis 层添加缓存，进一步提升性能

## 故障排查

### 问题：无法连接数据库

**解决方案**：
1. 检查 `data/` 目录是否存在且可写：`mkdir -p data && chmod 755 data`
2. 运行 `python database/init_db.py` 重新初始化

### 问题：Arduino 连接超时

**解决方案**：
1. 检查服务器是否运行：`curl http://your-server-ip:8000/api/health`
2. 检查网络连接和防火墙：`telnet your-server-ip 8000`
3. 检查服务器日志：`sudo journalctl -u ee3070-server`

### 问题：导入 CSV 数据失败

**解决方案**：
1. 确保 `dataset.csv` 和 `coupon_state.csv` 在项目根目录（`../`）
2. 检查 CSV 格式和编码（应为 UTF-8）
3. 手动运行 `python database/init_db.py`

## 进阶用法

### 使用 PostgreSQL

```bash
# 1. 安装 PostgreSQL 驱动
pip install psycopg2-binary

# 2. 修改 DATABASE_URL
export DATABASE_URL="postgresql://user:password@localhost:5432/ee3070"

# 3. 重新初始化数据库
python database/init_db.py
```

### Docker 部署

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

```bash
docker build -t ee3070-server .
docker run -p 8000:8000 -e DEBUG=False ee3070-server
```

## 许可证

MIT

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。
