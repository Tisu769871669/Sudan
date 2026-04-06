#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "该脚本需要 root 权限执行。" >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "当前系统没有 systemctl，无法安装 systemd 服务。" >&2
  exit 1
fi

if ! command -v openclaw >/dev/null 2>&1; then
  echo "缺少 openclaw 命令。" >&2
  exit 1
fi

OPENCLAW_BIN="$(command -v openclaw)"
SERVICE_PATH="/etc/systemd/system/openclaw-gateway.service"
SERVICE_USER="${SUDO_USER:-root}"
SERVICE_HOME="$(getent passwd "$SERVICE_USER" | cut -d: -f6)"

if [[ -z "$SERVICE_HOME" ]]; then
  SERVICE_HOME="/root"
fi

cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$SERVICE_HOME
Environment=HOME=$SERVICE_HOME
ExecStart=$OPENCLAW_BIN gateway run
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now openclaw-gateway.service
systemctl status openclaw-gateway.service --no-pager --lines=20 || true

echo "已安装并启动 systemd 服务: $SERVICE_PATH"
