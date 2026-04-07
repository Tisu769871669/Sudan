#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "该脚本需要 root 权限执行。" >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "当前系统没有 systemctl。" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "缺少 node 命令，请先安装 Node.js 20+。" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$ROOT_DIR/node-services/agent-bridge"
ENV_FILE="$SERVICE_DIR/.env"
SERVICE_USER="$(id -un)"
SERVICE_HOME="$(getent passwd "$SERVICE_USER" | cut -d: -f6)"
NODE_BIN="$(command -v node)"
SERVICE_PATH="/etc/systemd/system/openclaw-agent-bridge.service"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "缺少环境文件: $ENV_FILE" >&2
  echo "请先从 .env.example 复制一份 .env 并填写 token。" >&2
  exit 1
fi

cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=Sudan OpenClaw Agent Bridge
After=network-online.target openclaw-gateway.service
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$SERVICE_DIR
Environment=HOME=$SERVICE_HOME
EnvironmentFile=$ENV_FILE
ExecStart=$NODE_BIN $SERVICE_DIR/src/server.js
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now openclaw-agent-bridge.service
sleep 2
systemctl status openclaw-agent-bridge.service --no-pager --lines=20 || true

if ! systemctl is-active --quiet openclaw-agent-bridge.service; then
  echo "openclaw-agent-bridge.service 启动失败，最近日志如下：" >&2
  journalctl -u openclaw-agent-bridge.service -n 50 --no-pager >&2 || true
  exit 1
fi

echo "已安装并启动: /etc/systemd/system/openclaw-agent-bridge.service"
