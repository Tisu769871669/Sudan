#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${TARGET_DIR:-$HOME/.openclaw/workspace/skills}"

mkdir -p "$TARGET_DIR"
rm -rf "$TARGET_DIR/metast-product-list" "$TARGET_DIR/metast-delivery-express-list" "$TARGET_DIR/metast-mcp"
cp -R "$ROOT_DIR/skills/metast-mcp" "$TARGET_DIR/metast-mcp"
if [[ -f "$ROOT_DIR/.env.metast" ]]; then
  cp "$ROOT_DIR/.env.metast" "$TARGET_DIR/metast-mcp/.env.metast"
  chmod 600 "$TARGET_DIR/metast-mcp/.env.metast"
fi

echo "Installed skills to: $TARGET_DIR"
echo "- metast-mcp"
if [[ -f "$TARGET_DIR/metast-mcp/.env.metast" ]]; then
  echo "Copied Metast MCP env file to: $TARGET_DIR/metast-mcp/.env.metast"
fi
echo
echo "If no .env.metast file was copied, remember to export:"
echo "  METAST_MCP_BASE_URL=https://lx.metast.cn"
echo "  METAST_MCP_KEY=<your key>"
echo "  METAST_MCP_SECRET=<your secret>"
echo
echo "Test with:"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py product-list"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py product-list --name 商品名"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py delivery-express-list"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py order-list --no ORDER_NO"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py yugao-list"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py member-user-list --page-no 1 --page-size 20"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py member-user-order-list --page-no 1 --page-size 20 --user-id USER_ID"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py order-user-delivery --order-id ORDER_ID"
echo "  python3 \$HOME/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py im-group-list --page-no 1 --page-size 20"
