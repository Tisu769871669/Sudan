#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${TARGET_DIR:-$HOME/.openclaw/workspace/skills}"

mkdir -p "$TARGET_DIR"
rm -rf "$TARGET_DIR/metast-product-list" "$TARGET_DIR/metast-delivery-express-list"
cp -R "$ROOT_DIR/skills/metast-product-list" "$TARGET_DIR/metast-product-list"
cp -R "$ROOT_DIR/skills/metast-delivery-express-list" "$TARGET_DIR/metast-delivery-express-list"

echo "Installed skills to: $TARGET_DIR"
echo "- metast-product-list"
echo "- metast-delivery-express-list"
echo
echo "Remember to export:"
echo "  METAST_MCP_BASE_URL=https://lx.metast.cn"
echo "  METAST_MCP_KEY=<your key>"
echo "  METAST_MCP_SECRET=<your secret>"
