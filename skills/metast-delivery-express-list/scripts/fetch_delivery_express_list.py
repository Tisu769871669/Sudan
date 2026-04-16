#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("METAST_MCP_BASE_URL", "https://lx.metast.cn").rstrip("/")
MCP_KEY = os.environ.get("METAST_MCP_KEY", "")
MCP_SECRET = os.environ.get("METAST_MCP_SECRET", "")
URL = f"{BASE_URL}/app-api/mcp/api-mcp/deliveryExpressList"


def main() -> int:
    if not MCP_KEY or not MCP_SECRET:
        print("Missing METAST_MCP_KEY or METAST_MCP_SECRET.", file=sys.stderr)
        return 1

    request = Request(
        URL,
        method="GET",
        headers={
            "mcpKey": MCP_KEY,
            "mcpSecret": MCP_SECRET,
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
