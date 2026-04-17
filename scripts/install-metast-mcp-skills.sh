#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${TARGET_DIR:-$HOME/.openclaw/workspace/skills}"

mkdir -p "$TARGET_DIR"
rm -rf "$TARGET_DIR/metast-product-list" "$TARGET_DIR/metast-delivery-express-list" "$TARGET_DIR/metast-mcp"
cp -R "$ROOT_DIR/skills/metast-mcp" "$TARGET_DIR/metast-mcp"

echo "Installed skills to: $TARGET_DIR"
echo "- metast-mcp"
echo
echo "Remember to export:"
echo "  METAST_MCP_BASE_URL=https://lx.metast.cn"
echo "  METAST_MCP_KEY=<your key>"
echo "  METAST_MCP_SECRET=<your secret>"
echo
echo "Test with:"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py product-list"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py product-list --name 商品名"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py delivery-express-list"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py order-list --no ORDER_NO"
