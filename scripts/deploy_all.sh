#!/bin/bash
# 一键部署脚本 - 在腾讯云服务器上同时部署 Server 和 MCP
# 使用: bash deploy_all.sh

set -e

echo "======================================"
echo "EE3070 全栈部署脚本"
echo "======================================"

if [ "$EUID" -ne 0 ]; then 
    echo "Error: 请以 root 身份运行此脚本"
    exit 1
fi

# 检查是否已安装 git
if ! command -v git &> /dev/null; then
    echo "[1/3] 安装 Git..."
    apt-get update
    apt-get install -y git python3 python3-pip
    echo "✓ Git 及 Python 已安装"
fi

# 定义 GitHub 仓库 URL - 需要修改为实际的 URL
read -p "请输入 ee3070-server GitHub 仓库 URL (默认: https://github.com/your-username/ee3070-server.git): " server_repo
server_repo=${server_repo:-"https://github.com/your-username/ee3070-server.git"}

read -p "请输入 ee3070-mcp GitHub 仓库 URL (默认: https://github.com/your-username/ee3070-mcp.git): " mcp_repo
mcp_repo=${mcp_repo:-"https://github.com/your-username/ee3070-mcp.git"}

DEPLOY_DIR="/opt/ee3070"
mkdir -p $DEPLOY_DIR
cd $DEPLOY_DIR

echo ""
echo "======================================"
echo "[1/2] 部署 ee3070-server"
echo "======================================"
if [ -d "$DEPLOY_DIR/ee3070-server" ]; then
    cd ee3070-server && git pull origin main && cd ..
else
    git clone $server_repo ee3070-server
fi

cd ee3070-server
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
python3 database/init_db.py
deactivate

cat > /etc/systemd/system/ee3070-server.service << 'EOF'
[Unit]
Description=EE3070 Web Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ee3070/ee3070-server
ExecStart=/bin/bash -c "source venv/bin/activate && python3 main.py"
Restart=always
RestartSec=10
Environment="DEBUG=False"
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ee3070-server
systemctl start ee3070-server
cd ..

echo "✓ ee3070-server 部署完成"
echo ""

echo "======================================"
echo "[2/2] 部署 ee3070-mcp"
echo "======================================"
if [ -d "$DEPLOY_DIR/ee3070-mcp" ]; then
    cd ee3070-mcp && git pull origin main && cd ..
else
    git clone $mcp_repo ee3070-mcp
fi

cd ee3070-mcp
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

cat > /etc/systemd/system/ee3070-mcp.service << EOF
[Unit]
Description=EE3070 MCP Server
After=network.target ee3070-server.service
Wants=ee3070-server.service

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_DIR/ee3070-mcp
ExecStart=/bin/bash -c "source venv/bin/activate && python3 mcp/mcp_server.py"
Restart=always
RestartSec=10
Environment="DATABASE_URL=sqlite:///$DEPLOY_DIR/ee3070-server/data/ee3070.db"
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ee3070-mcp
systemctl start ee3070-mcp
cd ..

echo "✓ ee3070-mcp 部署完成"
echo ""

echo "======================================"
echo "✓ 部署完成！"
echo "======================================"
sleep 3

echo ""
echo "服务状态："
systemctl status ee3070-server --no-pager
echo ""
systemctl status ee3070-mcp --no-pager
echo ""

SERVER_IP=$(hostname -I | awk '{print $1}')
echo "访问地址："
echo "  API 文档: http://$SERVER_IP:8000/docs"
echo "  Health Check: http://$SERVER_IP:8000/api/health"
echo ""
echo "查看日志："
echo "  sudo journalctl -u ee3070-server -f"
echo "  sudo journalctl -u ee3070-mcp -f"
