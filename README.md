# EE3070 Event Server

一个 FastAPI Web 服务器，为 Arduino、Python GUI 和 MCP 提供结构化事件写入、业务数据管理和日志分析服务。

## 特性

- 🧩 **结构化事件模型**：统一记录商品录入、购物车扫描、标签同步、优惠券、结账、支付和错误事件
- 📊 **数据库存储**：使用 SQLite（默认）或 PostgreSQL，支持高并发写入和审计查询
- 🔍 **事件查询 API**：支持按设备、交易、状态、时间范围和实体类型检索
- 🤖 **MCP 集成**：通过 Model Context Protocol 为 AI 提供只读分析和聚合能力
- 🛡️ **写入鉴权**：使用独立的 `WRITE_API_KEY` 和 `READ_API_KEY`
- 📈 **高性能索引**：事件表配置了时间、设备、交易和实体索引，加速分析查询

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

### 事件 API

#### POST /api/events
上传单条结构化事件。

```bash
curl -X POST "http://localhost:8000/api/events?write_key=YOUR_WRITE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"label_sync","device_id":"gui_merged","peer_device_id":"epaper","sku":10000001,"name":"示例商品","price":9.99,"discount":0.8,"status":"ok"}'
```

#### POST /api/events/batch
批量上传多个事件。

```bash
curl -X POST "http://localhost:8000/api/events/batch?write_key=YOUR_WRITE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"event_type":"product_upsert","device_id":"gui"},{"event_type":"cart_scan","device_id":"gui"}]}'
```

#### GET /api/events/latest
获取最新匹配事件，用于 Arduino 或状态同步。

```bash
curl "http://localhost:8000/api/events/latest?read_key=YOUR_READ_API_KEY&event_type=label_sync"
```

#### GET /api/events
按条件分页查询事件。

```bash
curl "http://localhost:8000/api/events?read_key=YOUR_READ_API_KEY&event_type=cart_scan&limit=20&since=2026-04-12T00:00:00"
```

#### GET /api/events/summary
获取聚合摘要，用于 AI 分析。

```bash
curl "http://localhost:8000/api/events/summary?read_key=YOUR_READ_API_KEY&since=2026-04-12T00:00:00"
```

### 专门业务动作 API

#### POST /api/inventory/stock-in
商品入库动作（同时写入 `inventory_stock_in` 事件）。

```bash
curl -X POST "http://localhost:8000/api/inventory/stock-in?write_key=YOUR_WRITE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"sku":10000001,"quantity":50,"unit_cost":6.5,"name":"新品A","device_id":"warehouse_1"}'
```

#### POST /api/coupons/issue
优惠券发放动作（写入 `coupon_issue` 事件）。

```bash
curl -X POST "http://localhost:8000/api/coupons/issue?write_key=YOUR_WRITE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"code":"NEW2026","discount_rate":0.85,"issued_to_device_id":"cart_7","device_id":"admin_console"}'
```

#### POST /api/coupons/{code}/redeem
优惠券兑换动作（写入 `coupon_redeem` 事件，并置为无效）。

```bash
curl -X POST "http://localhost:8000/api/coupons/NEW2026/redeem?write_key=YOUR_WRITE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tx_id":8891,"amount_before":128.0,"amount_after":108.8,"device_id":"checkout_2"}'
```

#### POST /api/coupons/{code}/invalidate
优惠券作废动作（写入 `coupon_invalidate` 事件）。

```bash
curl -X POST "http://localhost:8000/api/coupons/NEW2026/invalidate?write_key=YOUR_WRITE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"reason":"manual_revoke","device_id":"admin_console"}'
```

#### POST /api/checkout
购物车成交动作（写入 `checkout_complete` 事件）。

```bash
curl -X POST "http://localhost:8000/api/checkout?write_key=YOUR_WRITE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tx_id":8891,"coupon_code":"NEW2026","device_id":"checkout_2","items":[{"sku":10000001,"quantity":2,"price":9.9,"discount":0.9}]}'
```

#### POST /api/payments
支付动作（写入 `payment_recorded` 事件）。

```bash
curl -X POST "http://localhost:8000/api/payments?write_key=YOUR_WRITE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tx_id":8891,"amount":108.8,"payment_method":"wechat","status":"paid","device_id":"checkout_2"}'
```

#### 读取辅助接口

```bash
curl "http://localhost:8000/api/health"
curl "http://localhost:8000/api/products?read_key=YOUR_READ_API_KEY"
curl "http://localhost:8000/api/coupons?read_key=YOUR_READ_API_KEY&valid_only=true"
```

## 配置

编辑 [config.py](config.py) 修改配置：

```python
# 数据库 URL
DATABASE_URL = "sqlite:///data/ee3070.db"  # 或 "postgresql://user:pass@localhost/ee3070"

# API 密钥
WRITE_API_KEY = "YOUR_WRITE_API_KEY"
READ_API_KEY = "YOUR_READ_API_KEY"

# 客户端重试节流（秒）
MIN_EVENT_RETRY_INTERVAL = 0.25
```

或通过环境变量：

```bash
export DATABASE_URL="sqlite:///data/ee3070.db"
export WRITE_API_KEY="your-write-key"
export READ_API_KEY="your-read-key"
export DEBUG="True"
```

## 数据库架构

### event_logs 表
主事件表，记录设备指令、商品、优惠券、交易和错误信息。

常用字段包括：
- `event_type`
- `device_id` / `peer_device_id`
- `entity_type` / `entity_id`
- `sku` / `name` / `price` / `discount` / `quantity`
- `coupon_code` / `tx_id`
- `request_id` / `trace_id`
- `status` / `error_code` / `error_message` / `latency_ms`

索引覆盖时间、设备、交易、优惠券和实体维度，适合 AI 做分组、过滤和异常分析。

### products 表
商品信息（从 dataset.csv 导入）

### coupons 表
优惠券信息（从 coupon_state.csv 导入）

## 迁移现有数据

如需导入旧历史数据，请使用一次性迁移脚本将历史记录写入新的事件表。

## 修改本地客户端

### Arduino (arduino-code-merged.ino)

**修改后：**
```cpp
const char* SERVER_HOST = "your-server-ip";
const uint16_t SERVER_PORT = 8000;
const char* LATEST_EVENT_PATH = "/api/events/latest?event_type=label_sync&read_key=YOUR_READ_API_KEY";
```

### Python GUI (RFID-write/gui_merged.py)

**修改后：**
```python
EVENT_CREATE_URL = "http://your-server-ip:8000/api/events"
```

### MATLAB (cart_exported.m)

**修改后：**
```matlab
url = "http://your-server-ip:8000/api/events?event_type=cart_scan";
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
