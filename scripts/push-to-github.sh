#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_URL="${1:-https://github.com/Tisu769871669/Sudan.git}"
COMMIT_MESSAGE="${2:-feat: add Sudan OpenClaw persona project}"

cd "$ROOT_DIR"

if ! command -v git >/dev/null 2>&1; then
  echo "缺少 git 命令。" >&2
  exit 1
fi

if [[ ! -d .git ]]; then
  git init
fi

git branch -M main

if git remote get-url origin >/dev/null 2>&1; then
  git remote remove origin
fi

git remote add origin "$REMOTE_URL"
git add .

if [[ -n "$(git status --porcelain)" ]]; then
  git commit -m "$COMMIT_MESSAGE"
else
  echo "当前没有新的变更需要提交。"
fi

git push -u origin main
