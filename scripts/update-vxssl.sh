#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "该脚本需要 root 权限执行。" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1 || ! command -v md5sum >/dev/null 2>&1; then
  echo "缺少 curl 或 md5sum。" >&2
  exit 1
fi

DOMAIN="${DOMAIN:-sdseoul.metast.cn}"
CERT_URL="${CERT_URL:-https://getssl.vx.link/66a9a94fbae44.crt}"
KEY_URL="${KEY_URL:-https://getssl.vx.link/66a9a94fbae44.key}"
CRT_PATH="${CRT_PATH:-/etc/nginx/ssl/$DOMAIN.crt}"
KEY_PATH="${KEY_PATH:-/etc/nginx/ssl/$DOMAIN.key}"

declare -A urls_and_paths=(
  ["$CERT_URL"]="$CRT_PATH"
  ["$KEY_URL"]="$KEY_PATH"
)

reload_required=false

for url in "${!urls_and_paths[@]}"; do
  local_path="${urls_and_paths[$url]}"
  temp_file="$(mktemp)"

  if ! curl -fsSL "$url" -o "$temp_file"; then
    echo "证书下载失败: $url" >&2
    rm -f "$temp_file"
    continue
  fi

  remote_md5="$(md5sum "$temp_file" | awk '{print $1}')"
  local_md5="$(md5sum "$local_path" 2>/dev/null | awk '{print $1}')"

  if [[ "$remote_md5" != "$local_md5" ]]; then
    mv "$temp_file" "$local_path"
    reload_required=true
  else
    rm -f "$temp_file"
  fi
done

if [[ "$reload_required" == true ]]; then
  chmod 600 "$KEY_PATH" 2>/dev/null || true
  chmod 644 "$CRT_PATH" 2>/dev/null || true
  nginx -t
  systemctl reload nginx
  echo "证书已更新，并已重载 nginx。"
else
  echo "证书未变化。"
fi
