#!/bin/bash
# 腾讯云服务器部署脚本 - 部署 ee3070-mcp
# 使用: bash deploy_mcp.sh [server_ip]

set -e

echo "======================================"
echo "EE3070 MCP 部署脚本"
echo "======================================"

# 配置
DEPLOY_DIR="/opt/ee3070"
GITHUB_REPO="https://github.com/your-username/ee3070-mcp.git"
SERVER_DB="/opt/ee3070/ee3070-server/data/ee3070.db"

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then 
    echo "Error: 请以 root 身份运行此脚本"
    exit 1
fi

echo "[1/5] 更新系统..."
apt-get update
apt-get install -y git python3 python3-pip python3-venv

echo "[2/5] 克隆 GitHub 仓库..."
if [ -d "$DEPLOY_DIR/ee3070-mcp" ]; then
    echo "  仓库已存在，更新中..."
    cd "$DEPLOY_DIR/ee3070-mcp"
    git pull origin main
else
    echo "  克隆仓库..."
    cd "$DEPLOY_DIR"
    git clone $GITHUB_REPO ee3070-mcp
fi

cd "$DEPLOY_DIR/ee3070-mcp"

echo "[3/5] 安装 Python 依赖..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo "[4/5] 配置环境变量..."
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
Environment="DATABASE_URL=sqlite:///$SERVER_DB"
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "[5/5] 启动 MCP 服务..."
systemctl daemon-reload
systemctl enable ee3070-mcp
systemctl start ee3070-mcp

echo ""
echo "======================================"
echo "✓ MCP 部署完成！"
echo "======================================"
echo ""
echo "服务状态:"
systemctl status ee3070-mcp --no-pager

echo ""
echo "测试 MCP:"
echo "  echo '{\"type\": \"list_tools\"}' | python3 $DEPLOY_DIR/ee3070-mcp/mcp/mcp_server.py"
echo ""
echo "查看日志:"
echo "  sudo journalctl -u ee3070-mcp -f"
