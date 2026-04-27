#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT_DIR = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT_DIR / ".automation-state"
DEFAULT_BASE_URL = "https://lx.metast.cn"
DEFAULT_PAGE_SIZE = 20
CHINA_TZ = ZoneInfo("Asia/Shanghai")


ENDPOINTS = {
    "product-list": "/app-api/mcp/api-mcp/productList",
    "yugao-list": "/app-api/mcp/api-mcp/yugaoList",
    "member-user-list": "/app-api/mcp/api-mcp/memberUserList",
    "member-user-order-list": "/app-api/mcp/api-mcp/memberUserOrderList",
    "order-user-delivery": "/app-api/mcp/api-mcp/orderUserdelivery",
    "im-group-list": "/prod-api/system/api/im/groupList",
    "send-chat-message": "/prod-api/system/api/im/sendChatMesage",
    "send-group-message": "/prod-api/system/api/im/sendGroupMesage",
}


@dataclass
class ApiClient:
    base_url: str
    mcp_key: str
    mcp_secret: str

    def get(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        path = ENDPOINTS[action]
        url = f"{self.base_url.rstrip('/')}{path}"
        clean_params = {
            key: value
            for key, value in (params or {}).items()
            if value is not None and value != ""
        }
        if clean_params:
            url = f"{url}?{urlencode(clean_params)}"

        request = Request(
            url,
            method="GET",
            headers={
                "mcpKey": self.mcp_key,
                "mcpSecret": self.mcp_secret,
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{action} HTTP {error.code}: {body}") from error
        except URLError as error:
            raise RuntimeError(f"{action} request failed: {error}") from error

        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"{action} returned non-JSON payload: {raw[:200]}") from error


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

    candidates = [
        ROOT_DIR / ".env.metast",
        Path.cwd() / ".env.metast",
        Path.home() / "Sudan" / ".env.metast",
        Path.home() / ".openclaw" / ".env.metast",
    ]
    for candidate in candidates:
        if candidate.exists():
            load_env_file(candidate)
            return


def create_client() -> ApiClient:
    load_default_env_files()
    mcp_key = os.environ.get("METAST_MCP_KEY", "")
    mcp_secret = os.environ.get("METAST_MCP_SECRET", "")
    if not mcp_key or not mcp_secret:
        raise SystemExit("Missing METAST_MCP_KEY or METAST_MCP_SECRET.")
    return ApiClient(
        base_url=os.environ.get("METAST_MCP_BASE_URL", DEFAULT_BASE_URL),
        mcp_key=mcp_key,
        mcp_secret=mcp_secret,
    )


def records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("list", "records", "rows", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    for key in ("list", "records", "rows", "items", "retArr"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def data_total(payload: dict[str, Any]) -> int | None:
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("total"), int):
        return data["total"]
    return None


def require_success(payload: dict[str, Any], action: str) -> None:
    code = payload.get("code")
    if code not in (0, 200, "0", "200", None):
        raise RuntimeError(f"{action} failed: code={code}, msg={payload.get('msg')}")


def fetch_pages(
    client: ApiClient,
    action: str,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_records: int | None = None,
    extra: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    page_no = 1
    while True:
        payload = client.get(
            action,
            {
                "pageNo": page_no,
                "pageSize": page_size,
                **(extra or {}),
            },
        )
        require_success(payload, action)
        page_records = records(payload)
        result.extend(page_records)
        total = data_total(payload)
        if max_records is not None and len(result) >= max_records:
            return result[:max_records]
        if not page_records or len(page_records) < page_size:
            return result
        if total is not None and len(result) >= total:
            return result
        page_no += 1


def group_targets(client: ApiClient, limit: int | None, page_size: int) -> list[dict[str, Any]]:
    groups = fetch_pages(
        client,
        "im-group-list",
        page_size=page_size,
        max_records=limit,
    )
    return [
        {
            "id": str(item.get("id") or ""),
            "gid": str(item.get("gid") or ""),
            "name": str(item.get("name") or item.get("corpName") or ""),
            "raw": item,
        }
        for item in groups
        if item.get("id")
    ]


def member_targets(client: ApiClient, limit: int | None, page_size: int) -> list[dict[str, Any]]:
    members = fetch_pages(
        client,
        "member-user-list",
        page_size=page_size,
        max_records=limit,
    )
    return [
        {
            "mobile": str(item.get("mobile") or ""),
            "name": str(item.get("name") or item.get("nickname") or ""),
            "userId": item.get("id"),
            "raw": item,
        }
        for item in members
        if item.get("mobile")
    ]


def explicit_member_targets(mobiles: list[str] | None, mobile_csv: str | None) -> list[dict[str, Any]]:
    values: list[str] = []
    values.extend(mobiles or [])
    if mobile_csv:
        values.extend(mobile_csv.split(","))

    result = []
    seen = set()
    for value in values:
        mobile = str(value).strip()
        if not mobile or mobile in seen:
            continue
        seen.add(mobile)
        result.append(
            {
                "mobile": mobile,
                "name": "",
                "userId": None,
                "raw": {"mobile": mobile},
            }
        )
    return result


def money(value: Any) -> str:
    try:
        cents = int(value)
    except (TypeError, ValueError):
        return ""
    return f"{cents / 100:.2f}元"


def strip_html(value: Any) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def product_summary(item: dict[str, Any]) -> str:
    parts = [str(item.get("name") or "").replace("\n", " ").strip()]
    price = money(item.get("price"))
    if price:
        parts.append(price)
    if item.get("stock") is not None:
        parts.append(f"库存{item.get('stock')}")
    intro = strip_html(item.get("introduction"))
    if intro:
        parts.append(intro[:36])
    return "，".join(part for part in parts if part)


def build_vegetable_message(products: list[dict[str, Any]]) -> str:
    available = [
        item
        for item in products
        if str(item.get("status", "1")) == "1" and int(item.get("stock") or 0) > 0
    ]
    selected = available[:5] or products[:5]
    lines = ["今日农场蔬菜可以看这几款，都是现有上架信息："]
    for item in selected:
        lines.append(f"- {product_summary(item)}")
    lines.append("您想要哪款，我可以继续帮您看详情。")
    return "\n".join(lines)


def format_open_time(value: Any) -> str:
    try:
        timestamp = int(value) / 1000
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(timestamp, CHINA_TZ).strftime("%m月%d日 %H:%M")


def build_live_message(previews: list[dict[str, Any]], phase: str) -> str:
    preview = previews[0] if previews else {}
    title = str(preview.get("title") or "今晚直播").strip()
    name = str(preview.get("name") or "").strip()
    open_time = format_open_time(preview.get("openTime"))
    time_text = f"，时间是 {open_time}" if open_time else ""
    owner_text = f"{name} " if name else ""
    if phase == "final":
        return f"{owner_text}{title}{time_text}。直播马上开始，大家有空可以点进来看看。"
    if phase == "link":
        return f"{owner_text}{title}{time_text}。直播入口已经准备好了，方便的话现在就可以进来。"
    return f"{owner_text}{title}{time_text}。今天有直播提醒，别错过。"


def build_private_greeting(args: argparse.Namespace) -> str:
    if args.content:
        return args.content
    if args.content_file:
        return Path(args.content_file).read_text(encoding="utf-8").strip()

    fragments = ["早安～"]
    if args.weather_text:
        fragments.append(args.weather_text.strip())
    if args.holiday_text:
        fragments.append(args.holiday_text.strip())
    fragments.append("今天也记得照顾好自己。")
    fragments.append("黄精熟地按平时节奏坚持就好，有不舒服或疑问随时找我。")
    return "".join(fragments)


def send_group(client: ApiClient, group_id: str, content: str) -> dict[str, Any]:
    return client.get("send-group-message", {"groupId": group_id, "content": content})


def send_chat(client: ApiClient, mobile: str, content: str) -> dict[str, Any]:
    return client.get("send-chat-message", {"mobile": mobile, "content": content})


def emit_plan(plan: dict[str, Any]) -> None:
    print(json.dumps(plan, ensure_ascii=False, indent=2))


def execute_group_plan(client: ApiClient, targets: list[dict[str, Any]], content: str, execute: bool) -> list[dict[str, Any]]:
    results = []
    for target in targets:
        row = {
            "groupId": target["id"],
            "gid": target.get("gid", ""),
            "groupName": target["name"],
            "content": content,
            "executed": execute,
        }
        if execute:
            payload = send_group(client, target["id"], content)
            row["result"] = {"code": payload.get("code"), "msg": payload.get("msg")}
            time.sleep(0.2)
        results.append(row)
    return results


def execute_member_plan(client: ApiClient, targets: list[dict[str, Any]], content: str, execute: bool) -> list[dict[str, Any]]:
    results = []
    for target in targets:
        row = {
            "mobile": target["mobile"],
            "name": target["name"],
            "content": content,
            "executed": execute,
        }
        if execute:
            payload = send_chat(client, target["mobile"], content)
            row["result"] = {"code": payload.get("code"), "msg": payload.get("msg")}
            time.sleep(0.2)
        results.append(row)
    return results


def command_vegetable_push(args: argparse.Namespace) -> None:
    client = create_client()
    products_payload = client.get("product-list", {"name": args.keyword})
    require_success(products_payload, "product-list")
    products = records(products_payload)
    content = args.content or build_vegetable_message(products)
    targets = group_targets(client, args.group_limit, args.page_size)
    emit_plan(
        {
            "task": "vegetable-push",
            "mode": "execute" if args.execute else "dry-run",
            "keyword": args.keyword,
            "productCount": len(products),
            "targetCount": len(targets),
            "messages": execute_group_plan(client, targets, content, args.execute),
        }
    )


def command_live_reminder(args: argparse.Namespace) -> None:
    client = create_client()
    payload = client.get("yugao-list")
    require_success(payload, "yugao-list")
    previews = records(payload)
    content = args.content or build_live_message(previews, args.phase)
    targets = group_targets(client, args.group_limit, args.page_size)
    emit_plan(
        {
            "task": "live-reminder",
            "mode": "execute" if args.execute else "dry-run",
            "phase": args.phase,
            "previewCount": len(previews),
            "targetCount": len(targets),
            "messages": execute_group_plan(client, targets, content, args.execute),
        }
    )


def command_private_greeting(args: argparse.Namespace) -> None:
    client = create_client()
    content = build_private_greeting(args)
    targets = explicit_member_targets(args.mobile, args.mobiles) or member_targets(client, args.member_limit, args.page_size)
    emit_plan(
        {
            "task": "private-greeting",
            "mode": "execute" if args.execute else "dry-run",
            "targetCount": len(targets),
            "messages": execute_member_plan(client, targets, content, args.execute),
        }
    )


def load_state(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        return {"notified": {}}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"notified": {}}


def save_state(file_path: Path, state: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(file_path.suffix + f".{os.getpid()}.tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(file_path)


def order_key(order: dict[str, Any], status: int) -> str:
    raw_id = order.get("id") or order.get("orderId") or order.get("no") or order.get("orderNo")
    return f"{raw_id or json.dumps(order, sort_keys=True, ensure_ascii=False)[:120]}::{status}"


def build_order_message(member: dict[str, Any], order: dict[str, Any], status: int) -> str:
    name = member.get("name") or "您好"
    order_no = order.get("no") or order.get("orderNo") or order.get("id") or ""
    suffix = f"订单 {order_no} " if order_no else "您的订单"
    if status in (2, 20):
        return f"{name}～{suffix}物流有更新了，您这边留意一下包裹信息。"
    if status in (3, 30):
        return f"{name}～看到{suffix}快到/已到附近了，您这边记得留意签收。"
    if status in (4, 40):
        return f"{name}～看到{suffix}已经签收了，您方便时检查一下包裹是否完好。"
    return f"{name}～{suffix}状态有更新，您这边可以留意一下。"


def command_order_scan(args: argparse.Namespace) -> None:
    client = create_client()
    members = member_targets(client, args.member_limit, args.page_size)
    status_values = [int(item.strip()) for item in args.statuses.split(",") if item.strip()]
    state_path = Path(args.state_file) if args.state_file else STATE_DIR / "order-notifications.json"
    state = load_state(state_path)
    notified = state.setdefault("notified", {})
    messages = []

    for member in members:
        for status in status_values:
            payload = client.get(
                "member-user-order-list",
                {
                    "pageNo": 1,
                    "pageSize": args.order_page_size,
                    "mobile": member["mobile"],
                    "status": status,
                    "userId": member.get("userId") or "",
                },
            )
            require_success(payload, "member-user-order-list")
            for order in records(payload):
                key = order_key(order, status)
                if key in notified:
                    continue
                content = build_order_message(member, order, status)
                row = {
                    "mobile": member["mobile"],
                    "name": member["name"],
                    "status": status,
                    "orderKey": key,
                    "content": content,
                    "executed": args.execute,
                }
                if args.execute:
                    result = send_chat(client, member["mobile"], content)
                    row["result"] = {"code": result.get("code"), "msg": result.get("msg")}
                    notified[key] = {"mobile": member["mobile"], "status": status, "sentAt": datetime.now(CHINA_TZ).isoformat()}
                    time.sleep(0.2)
                messages.append(row)

    if args.execute:
        save_state(state_path, state)

    emit_plan(
        {
            "task": "order-scan",
            "mode": "execute" if args.execute else "dry-run",
            "memberCount": len(members),
            "statuses": status_values,
            "messageCount": len(messages),
            "stateFile": str(state_path),
            "messages": messages,
        }
    )


def command_api_check(args: argparse.Namespace) -> None:
    client = create_client()
    checks = []
    for action, params in [
        ("yugao-list", {}),
        ("product-list", {"name": args.product_keyword}),
        ("member-user-list", {"pageNo": 1, "pageSize": 1}),
        ("im-group-list", {"pageNo": 1, "pageSize": 1}),
    ]:
        payload = client.get(action, params)
        checks.append(
            {
                "action": action,
                "code": payload.get("code"),
                "msg": payload.get("msg"),
                "records": len(records(payload)),
                "keys": sorted(records(payload)[0].keys()) if records(payload) else [],
            }
        )
    emit_plan({"task": "api-check", "checks": checks})


def add_common_send_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--execute", action="store_true", help="Actually send messages. Default is dry-run.")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sudan customer-service daily automation helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    api_check = subparsers.add_parser("api-check", help="Check read-only API availability.")
    api_check.add_argument("--product-keyword", default="蔬菜")
    api_check.set_defaults(func=command_api_check)

    vegetable = subparsers.add_parser("vegetable-push", help="Build/send daily vegetable group push.")
    add_common_send_flags(vegetable)
    vegetable.add_argument("--keyword", default="蔬菜")
    vegetable.add_argument("--group-limit", type=int, default=3, help="Limit target groups. Use 0 for all groups.")
    vegetable.add_argument("--content", help="Override generated message content.")
    vegetable.set_defaults(func=lambda args: normalize_limits(args, "group_limit", command_vegetable_push))

    live = subparsers.add_parser("live-reminder", help="Build/send live preview group reminder.")
    add_common_send_flags(live)
    live.add_argument("--phase", choices=["pre", "final", "link"], default="pre")
    live.add_argument("--group-limit", type=int, default=3, help="Limit target groups. Use 0 for all groups.")
    live.add_argument("--content", help="Override generated message content.")
    live.set_defaults(func=lambda args: normalize_limits(args, "group_limit", command_live_reminder))

    greeting = subparsers.add_parser("private-greeting", help="Build/send private morning greetings.")
    add_common_send_flags(greeting)
    greeting.add_argument("--member-limit", type=int, default=10, help="Limit target members. Use 0 for all members.")
    greeting.add_argument("--mobile", action="append", help="Exact mobile target. Can be used multiple times.")
    greeting.add_argument("--mobiles", help="Comma separated exact mobile targets.")
    greeting.add_argument("--weather-text", help="Weather text from OpenClaw search or external source.")
    greeting.add_argument("--holiday-text", help="Holiday/solar-term text from OpenClaw search or external source.")
    greeting.add_argument("--content", help="Exact message content.")
    greeting.add_argument("--content-file", help="Read exact message content from file.")
    greeting.set_defaults(func=lambda args: normalize_limits(args, "member_limit", command_private_greeting))

    order_scan = subparsers.add_parser("order-scan", help="Poll member orders and prepare private notifications.")
    add_common_send_flags(order_scan)
    order_scan.add_argument("--member-limit", type=int, default=20, help="Limit target members. Use 0 for all members.")
    order_scan.add_argument("--statuses", default="2,3,4", help="Comma separated order statuses to scan.")
    order_scan.add_argument("--order-page-size", type=int, default=10)
    order_scan.add_argument("--state-file", help="Notification state file.")
    order_scan.set_defaults(func=lambda args: normalize_limits(args, "member_limit", command_order_scan))

    return parser


def normalize_limits(args: argparse.Namespace, attr: str, func: Any) -> None:
    if getattr(args, attr) == 0:
        setattr(args, attr, None)
    func(args)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
