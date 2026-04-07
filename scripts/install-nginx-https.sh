#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "该脚本需要 root 权限执行。" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "缺少 curl，请先安装。" >&2
  exit 1
fi

DOMAIN="${DOMAIN:-sdseoul.metast.cn}"
BRIDGE_PORT="${BRIDGE_PORT:-9070}"
CERT_URL="${CERT_URL:-https://getssl.vx.link/66a9a94fbae44.crt}"
KEY_URL="${KEY_URL:-https://getssl.vx.link/66a9a94fbae44.key}"
SSL_DIR="${SSL_DIR:-/etc/nginx/ssl}"
NGINX_CONF_DIR="${NGINX_CONF_DIR:-/etc/nginx/sites-available}"
NGINX_ENABLED_DIR="${NGINX_ENABLED_DIR:-/etc/nginx/sites-enabled}"
CONF_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/deploy/nginx/sdseoul.metast.cn.conf"
CONF_TARGET="$NGINX_CONF_DIR/$DOMAIN.conf"
ENABLED_TARGET="$NGINX_ENABLED_DIR/$DOMAIN.conf"
CRT_PATH="$SSL_DIR/$DOMAIN.crt"
KEY_PATH="$SSL_DIR/$DOMAIN.key"

export DEBIAN_FRONTEND=noninteractive

if ! command -v nginx >/dev/null 2>&1; then
  apt-get update
  apt-get install -y nginx
fi

mkdir -p "$SSL_DIR"

curl -fsSL "$CERT_URL" -o "$CRT_PATH"
curl -fsSL "$KEY_URL" -o "$KEY_PATH"
chmod 600 "$KEY_PATH"
chmod 644 "$CRT_PATH"

mkdir -p "$NGINX_CONF_DIR" "$NGINX_ENABLED_DIR"
cp "$CONF_SOURCE" "$CONF_TARGET"

sed -i "s/sdseoul\\.metast\\.cn/$DOMAIN/g" "$CONF_TARGET"
sed -i "s|127.0.0.1:9070|127.0.0.1:$BRIDGE_PORT|g" "$CONF_TARGET"

ln -sf "$CONF_TARGET" "$ENABLED_TARGET"
rm -f "$NGINX_ENABLED_DIR/default"

nginx -t
systemctl enable nginx
systemctl restart nginx

echo "Nginx HTTPS 反代已安装完成。"
echo "域名: $DOMAIN"
echo "证书: $CRT_PATH"
echo "私钥: $KEY_PATH"
echo "反代目标: http://127.0.0.1:$BRIDGE_PORT"
