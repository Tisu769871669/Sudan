#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ENDPOINTS = {
    "product-list": "/app-api/mcp/api-mcp/productList",
    "delivery-express-list": "/app-api/mcp/api-mcp/deliveryExpressList",
    "order-list": "/app-api/mcp/api-mcp/orderList",
    "yugao-list": "/app-api/mcp/api-mcp/yugaoList",
    "member-user-list": "/app-api/mcp/api-mcp/memberUserList",
    "member-user-order-list": "/app-api/mcp/api-mcp/memberUserOrderList",
    "order-user-delivery": "/app-api/mcp/api-mcp/orderUserdelivery",
    "im-group-list": "/system/api/im/groupList",
    "send-chat-message": "/system/api/im/sendChatMesage",
    "send-group-message": "/system/api/im/sendGroupMesage",
}

PAGINATED_ACTIONS = {
    "member-user-list",
    "member-user-order-list",
    "im-group-list",
}


def require_param(action: str, params: dict[str, object], key: str, label: str) -> object:
    value = params.get(key)
    if value is None or value == "":
        raise ValueError(f"{action} requires {label}")
    return value


def load_env_file(file_path: Path) -> None:
    if not file_path.exists():
        return
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def load_default_env_files() -> None:
    explicit_path = os.environ.get("METAST_MCP_ENV_FILE")
    if explicit_path:
        load_env_file(Path(explicit_path).expanduser())
        return

    script_root = Path(__file__).resolve().parents[1]
    candidates = [
        script_root / ".env.metast",
        Path.cwd() / ".env.metast",
        Path.home() / "Sudan" / ".env.metast",
        Path.home() / ".openclaw" / ".env.metast",
    ]
    for candidate in candidates:
        if candidate.exists():
            load_env_file(candidate)
            return


def build_url(base_url: str, action: str, params: dict[str, object]) -> str:
    path = ENDPOINTS[action]
    url = f"{base_url.rstrip('/')}{path}"
    query: dict[str, object] = {}

    if action == "product-list" and params.get("name"):
        query["name"] = params["name"]

    if action == "order-list":
        query["no"] = require_param(action, params, "no", "--no ORDER_NO")

    if action in PAGINATED_ACTIONS:
        query["pageNo"] = require_param(action, params, "page_no", "--page-no PAGE_NO")
        query["pageSize"] = require_param(
            action, params, "page_size", "--page-size PAGE_SIZE"
        )

    if action == "member-user-order-list":
        query["userId"] = require_param(action, params, "user_id", "--user-id USER_ID")

    if action == "order-user-delivery":
        query["orderId"] = require_param(
            action, params, "order_id", "--order-id ORDER_ID"
        )

    if action == "send-chat-message":
        query["mobile"] = require_param(action, params, "mobile", "--mobile MOBILE")
        query["content"] = require_param(action, params, "content", "--content CONTENT")

    if action == "send-group-message":
        query["groupId"] = require_param(
            action, params, "group_id", "--group-id GROUP_ID"
        )
        query["content"] = require_param(action, params, "content", "--content CONTENT")

    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch data from Metast MCP endpoints.")
    parser.add_argument(
        "action",
        choices=sorted(ENDPOINTS),
        help="Which endpoint to call",
    )
    parser.add_argument("--name", help="Product name filter, optional for product-list")
    parser.add_argument("--no", help="Order number, required for order-list")
    parser.add_argument("--page-no", type=int, help="Page number for paginated endpoints")
    parser.add_argument("--page-size", type=int, help="Page size for paginated endpoints")
    parser.add_argument("--user-id", type=int, help="User ID for member-user-order-list")
    parser.add_argument("--order-id", type=int, help="Order ID for order-user-delivery")
    parser.add_argument("--mobile", help="Mobile number for send-chat-message")
    parser.add_argument("--group-id", help="Group ID for send-group-message")
    parser.add_argument("--content", help="Message content for send message endpoints")
    args = parser.parse_args()

    load_default_env_files()

    base_url = os.environ.get("METAST_MCP_BASE_URL", "https://lx.metast.cn")
    mcp_key = os.environ.get("METAST_MCP_KEY", "")
    mcp_secret = os.environ.get("METAST_MCP_SECRET", "")

    if not mcp_key or not mcp_secret:
        print("Missing METAST_MCP_KEY or METAST_MCP_SECRET.", file=sys.stderr)
        return 1

    try:
        url = build_url(
            base_url,
            args.action,
            {
                "name": args.name or "",
                "no": args.no or "",
                "page_no": args.page_no,
                "page_size": args.page_size,
                "user_id": args.user_id,
                "order_id": args.order_id,
                "mobile": args.mobile or "",
                "group_id": args.group_id or "",
                "content": args.content or "",
            },
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    request = Request(
        url,
        method="GET",
        headers={
            "mcpKey": mcp_key,
            "mcpSecret": mcp_secret,
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
            payload = response.read().decode("utf-8")
            try:
                parsed = json.loads(payload)
                print(json.dumps(parsed, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                print(payload)
    except HTTPError as error:
        print(
            f"HTTP {error.code}: {error.read().decode('utf-8', errors='replace')}",
            file=sys.stderr,
        )
        return 1
    except URLError as error:
        print(f"Request failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
