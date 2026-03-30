#!/bin/bash
# 腾讯云服务器部署脚本 - 部署 ee3070-server
# 使用: bash deploy_server.sh [server_ip]

set -e  # 任何命令失败则退出

echo "======================================"
echo "EE3070 Server 部署脚本"
echo "======================================"

# 配置
DEPLOY_DIR="/opt/ee3070"
SERVER_PORT="8000"
GITHUB_REPO="https://github.com/your-username/ee3070-server.git"

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then 
    echo "Error: 请以 root 身份运行此脚本"
    exit 1
fi

echo "[1/6] 更新系统并安装依赖..."
apt-get update
apt-get install -y git python3 python3-pip python3-venv wget curl

echo "[2/6] 创建部署目录..."
mkdir -p $DEPLOY_DIR
cd $DEPLOY_DIR

echo "[3/6] 克隆 GitHub 仓库..."
if [ -d "$DEPLOY_DIR/ee3070-server" ]; then
    echo "  仓库已存在，更新中..."
    cd ee3070-server
    git pull origin main
    cd ..
else
    echo "  克隆仓库..."
    git clone $GITHUB_REPO ee3070-server
fi

cd ee3070-server

echo "[4/6] 安装 Python 依赖..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo "[5/6] 初始化数据库..."
source venv/bin/activate
python3 database/init_db.py
deactivate

echo "[6/6] 配置 systemd 服务..."
cat > /etc/systemd/system/ee3070-server.service << EOF
[Unit]
Description=EE3070 Web Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_DIR/ee3070-server
ExecStart=/bin/bash -c "source venv/bin/activate && python3 main.py"
Restart=always
RestartSec=10
Environment="DEBUG=False"

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ee3070-server
systemctl start ee3070-server

echo ""
echo "======================================"
echo "✓ 部署完成！"
echo "======================================"
echo ""
echo "服务状态检查:"
systemctl status ee3070-server --no-pager

echo ""
echo "访问 API:"
echo "  API 文档: http://$(hostname -I | awk '{print $1}'):$SERVER_PORT/docs"
echo "  Health: http://$(hostname -I | awk '{print $1}'):$SERVER_PORT/api/health"
echo ""
echo "查看日志:"
echo "  sudo journalctl -u ee3070-server -f"
echo ""
echo "停止服务:"
echo "  sudo systemctl stop ee3070-server"
echo ""
echo "重启服务:"
echo "  sudo systemctl restart ee3070-server"
