#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令: $1" >&2
    exit 1
  fi
}

require_cmd git
require_cmd python3
require_cmd openclaw

ensure_venv_support() {
  if python3 -m venv "$VENV_DIR" >/dev/null 2>&1; then
    return
  fi

  if command -v apt-get >/dev/null 2>&1 && [[ "$(id -u)" -eq 0 ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y python3-venv python3-pip
    python3 -m venv "$VENV_DIR"
    return
  fi

  echo "当前环境缺少 python3-venv，且脚本无法自动安装。" >&2
  echo "请先安装：apt-get update && apt-get install -y python3-venv python3-pip" >&2
  exit 1
}

if [[ ! -d "$VENV_DIR" ]]; then
  ensure_venv_support
fi

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  rm -rf "$VENV_DIR"
  ensure_venv_support
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip >/dev/null
python -m pip install PyYAML >/dev/null

echo "环境准备完成。"
echo "虚拟环境: $VENV_DIR"
