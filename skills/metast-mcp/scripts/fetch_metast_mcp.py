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
}


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


def build_url(base_url: str, action: str, order_no: str, product_name: str) -> str:
    path = ENDPOINTS[action]
    url = f"{base_url.rstrip('/')}{path}"
    query = {}
    if action == "product-list" and product_name:
        query["name"] = product_name
    if action == "order-list":
        if not order_no:
            raise ValueError("order-list requires --no ORDER_NO")
        query["no"] = order_no
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch data from Metast MCP endpoints.")
    parser.add_argument(
        "action",
        choices=["product-list", "delivery-express-list", "order-list"],
        help="Which endpoint to call",
    )
    parser.add_argument("--name", help="Product name filter, optional for product-list")
    parser.add_argument("--no", help="Order number, required for order-list")
    args = parser.parse_args()

    load_default_env_files()

    base_url = os.environ.get("METAST_MCP_BASE_URL", "https://lx.metast.cn")
    mcp_key = os.environ.get("METAST_MCP_KEY", "")
    mcp_secret = os.environ.get("METAST_MCP_SECRET", "")

    if not mcp_key or not mcp_secret:
        print("Missing METAST_MCP_KEY or METAST_MCP_SECRET.", file=sys.stderr)
        return 1

    try:
        url = build_url(base_url, args.action, args.no or "", args.name or "")
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
