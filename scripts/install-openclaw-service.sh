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

BASH_BIN="$(command -v bash || true)"
if [[ -z "$BASH_BIN" ]]; then
  echo "缺少 bash 命令。" >&2
  exit 1
fi

OPENCLAW_BIN="$(command -v openclaw)"
OPENCLAW_DIR="$(dirname "$OPENCLAW_BIN")"
SYSTEM_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

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
Environment=PATH=$OPENCLAW_DIR:$SYSTEM_PATH
ExecStart=$BASH_BIN -lc 'source ~/.profile >/dev/null 2>&1 || true; source ~/.bashrc >/dev/null 2>&1 || true; exec "$OPENCLAW_BIN" gateway run'
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now openclaw-gateway.service
systemctl status openclaw-gateway.service --no-pager --lines=20 || true

if ! systemctl is-active --quiet openclaw-gateway.service; then
  echo "openclaw-gateway.service 启动失败，最近日志如下：" >&2
  journalctl -u openclaw-gateway.service -n 50 --no-pager >&2 || true
  exit 1
fi

echo "已安装并启动 systemd 服务: $SERVICE_PATH"
