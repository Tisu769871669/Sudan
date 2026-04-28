#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
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
DEFAULT_COPYWRITER_AGENT_ID = "main"
DEFAULT_COPYWRITER_TIMEOUT_SECONDS = 90
COPY_BLOCKED_TERMS = ["治愈", "根治", "保证有效", "替代医生", "包治", "立刻见效"]


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


@dataclass
class CopyRequest:
    task: str
    channel: str
    fallback: str
    context: dict[str, Any]
    tone: str = "贴心、自然、克制的养生顾问"


@dataclass
class DailyCopyContext:
    today: str
    weather_text: str = ""
    solar_term: str = ""
    holiday_text: str = ""
    live_context: list[dict[str, Any]] = field(default_factory=list)
    product_focus: list[str] = field(default_factory=list)


SOLAR_TERMS_BY_MONTH_DAY = {
    "02-03": "立春",
    "02-04": "立春",
    "02-18": "雨水",
    "02-19": "雨水",
    "03-05": "惊蛰",
    "03-06": "惊蛰",
    "03-20": "春分",
    "03-21": "春分",
    "04-04": "清明",
    "04-05": "清明",
    "04-19": "谷雨",
    "04-20": "谷雨",
    "05-05": "立夏",
    "05-06": "立夏",
    "05-20": "小满",
    "05-21": "小满",
    "06-05": "芒种",
    "06-06": "芒种",
    "06-21": "夏至",
    "06-22": "夏至",
    "07-06": "小暑",
    "07-07": "小暑",
    "07-22": "大暑",
    "07-23": "大暑",
    "08-07": "立秋",
    "08-08": "立秋",
    "08-22": "处暑",
    "08-23": "处暑",
    "09-07": "白露",
    "09-08": "白露",
    "09-22": "秋分",
    "09-23": "秋分",
    "10-08": "寒露",
    "10-09": "寒露",
    "10-23": "霜降",
    "10-24": "霜降",
    "11-07": "立冬",
    "11-08": "立冬",
    "11-22": "小雪",
    "11-23": "小雪",
    "12-06": "大雪",
    "12-07": "大雪",
    "12-21": "冬至",
    "12-22": "冬至",
    "01-05": "小寒",
    "01-06": "小寒",
    "01-20": "大寒",
    "01-21": "大寒",
}


PRIVATE_GREETING_STYLE_REFERENCES = [
    "每日养生不缺席 🌿",
    "记得食用黄精怀熟地黄，温和滋养身心",
    "贴上好视力眼贴，舒缓眼部疲劳",
    "愿日子温柔，身心安康，事事顺心，日日皆欢喜",
]


PRIVATE_GREETING_PRODUCT_FOCUS = ["黄精怀熟地黄", "好视力眼贴"]


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


def parse_agent_copy_output(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            payload, _ = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("agent copy output did not contain a JSON object")


def validate_generated_copy(content: str) -> None:
    text = str(content or "").strip()
    if not text:
        raise ValueError("generated copy is empty")
    for term in COPY_BLOCKED_TERMS:
        if term in text:
            raise ValueError(f"generated copy contains blocked term: {term}")


def build_copy_prompt(request: CopyRequest) -> str:
    return "\n".join(
        [
            "你是苏丹老师私域客服的文案助手，只负责生成可直接发送的中文文案。",
            "请根据任务上下文输出 JSON，禁止输出 Markdown、解释或多余文字。",
            "",
            "输出 JSON 格式：",
            '{"content":"可直接发送的文案或内部规划结果","riskLevel":"low","sendChannel":"group|private|internal","reason":"一句话说明"}',
            "",
            "硬性规则：",
            "- 语气亲切自然，可以适度使用小表情，但不要刷屏。",
            "- 大健康内容只能写日常养护建议，不能写医疗诊断或疗效承诺。",
            "- 禁止使用：治愈、根治、保证有效、替代医生、包治、立刻见效。",
            "- 如果是非卖货直播提醒，只写群发口径，不要写私发重点客户。",
            "- 如果信息不足，生成稳妥提醒，不要编造直播链接、价格、福利或医疗功效。",
            "",
            f"任务：{request.task}",
            f"发送渠道：{request.channel}",
            f"语气定位：{request.tone}",
            "上下文：",
            json.dumps(request.context, ensure_ascii=False, indent=2),
        ]
    )


def generate_agent_copy(
    request: CopyRequest,
    *,
    runner: Any | None = None,
    agent_id: str | None = None,
    timeout_seconds: int | None = None,
) -> tuple[str, dict[str, Any]]:
    try:
        prompt = build_copy_prompt(request)
        raw = runner(prompt) if runner else run_copywriter_agent(prompt, agent_id=agent_id, timeout_seconds=timeout_seconds)
        payload = parse_agent_copy_output(raw)
        content = str(payload.get("content") or "").strip()
        validate_generated_copy(content)
        send_channel = str(payload.get("sendChannel") or request.channel).strip() or request.channel
        return content, {
            "fallbackUsed": False,
            "riskLevel": str(payload.get("riskLevel") or ""),
            "sendChannel": send_channel,
            "reason": str(payload.get("reason") or ""),
        }
    except Exception as error:
        return request.fallback, {
            "fallbackUsed": True,
            "fallbackReason": str(error)[:240],
            "sendChannel": request.channel,
        }


def run_copywriter_agent(prompt: str, *, agent_id: str | None = None, timeout_seconds: int | None = None) -> str:
    resolved_agent_id = agent_id or os.environ.get("SUDAN_COPYWRITER_AGENT_ID") or DEFAULT_COPYWRITER_AGENT_ID
    resolved_timeout = int(timeout_seconds or os.environ.get("SUDAN_COPYWRITER_TIMEOUT_SECONDS") or DEFAULT_COPYWRITER_TIMEOUT_SECONDS)
    openclaw_bin = resolve_openclaw_bin(os.environ.get("SUDAN_COPYWRITER_OPENCLAW_BIN") or os.environ.get("OPENCLAW_BIN") or "openclaw")
    session_id = f"sudan_copywriter_{datetime.now(CHINA_TZ).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:12]}"
    args = [
        openclaw_bin,
        "agent",
        "--agent",
        resolved_agent_id,
        "--session-id",
        session_id,
        "--message",
        prompt,
        "--timeout",
        str(resolved_timeout),
    ]
    if os.environ.get("SUDAN_COPYWRITER_FORCE_LOCAL") == "1" or os.environ.get("OPENCLAW_FORCE_LOCAL") == "1":
        args.append("--local")
    env = {
        **os.environ,
        "OPENCLAW_HIDE_BANNER": "1",
        "OPENCLAW_SUPPRESS_NOTES": "1",
        "NO_COLOR": "1",
    }
    completed = subprocess.run(
        args,
        cwd=ROOT_DIR,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=resolved_timeout + 20,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"copywriter agent failed with code {completed.returncode}: {detail[:300]}")
    return "\n".join(part for part in [completed.stdout, completed.stderr] if part)


def resolve_openclaw_bin(value: str) -> str:
    if os.path.isabs(value) or os.sep in value or (os.altsep and os.altsep in value):
        return value
    found = shutil.which(value)
    if found:
        return found
    candidates = sorted(glob.glob("/root/.nvm/versions/node/*/bin/openclaw"), reverse=True)
    return candidates[0] if candidates else value


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


def parse_copy_date(value: Any | None = None) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return datetime.now(CHINA_TZ).date()
    return datetime.strptime(text, "%Y-%m-%d").date()


def solar_term_for_day(day: date) -> str:
    return SOLAR_TERMS_BY_MONTH_DAY.get(day.strftime("%m-%d"), "")


def build_daily_copy_context(
    *,
    weather_text: str = "",
    holiday_text: str = "",
    live_previews: list[dict[str, Any]] | None = None,
    now: Any | None = None,
) -> DailyCopyContext:
    today = parse_copy_date(now)
    solar_term = solar_term_for_day(today)
    holiday_parts = [str(holiday_text or "").strip()]
    if solar_term and solar_term not in holiday_parts[0]:
        holiday_parts.append(f"今日{solar_term}，适合顺着时节温和养护。")
    return DailyCopyContext(
        today=today.isoformat(),
        weather_text=str(weather_text or "").strip(),
        solar_term=solar_term,
        holiday_text=" ".join(part for part in holiday_parts if part),
        live_context=compact_live_context(live_previews or []),
        product_focus=PRIVATE_GREETING_PRODUCT_FOCUS.copy(),
    )


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


def build_vegetable_content(
    products: list[dict[str, Any]],
    *,
    copy_mode: str = "template",
    copy_runner: Any | None = None,
    agent_id: str | None = None,
    timeout_seconds: int | None = None,
) -> tuple[str, dict[str, Any]]:
    fallback = build_vegetable_message(products)
    if copy_mode != "agent":
        return fallback, {"fallbackUsed": False, "copyMode": "template", "sendChannel": "group"}
    context = {
        "products": [product_summary(item) for item in products[:8]],
        "requirement": "生成每日蔬菜群推送，结合季节和日常养生需求，给简单烹饪建议，避免夸大功效。",
    }
    return generate_agent_copy(
        CopyRequest(task="vegetable-push", channel="group", fallback=fallback, context=context),
        runner=copy_runner,
        agent_id=agent_id,
        timeout_seconds=timeout_seconds,
    )


def format_open_time(value: Any) -> str:
    try:
        timestamp = int(value) / 1000
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(timestamp, CHINA_TZ).strftime("%m月%d日 %H:%M")


def compact_live_context(previews: list[dict[str, Any]], limit: int = 2) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for preview in previews[:limit]:
        row: dict[str, Any] = {}
        for key in ("title", "name", "summary", "content"):
            value = strip_html(preview.get(key))
            if value:
                row[key] = value[:120]
        open_time = format_open_time(preview.get("openTime"))
        if open_time:
            row["openTimeText"] = open_time
        if row:
            result.append(row)
    return result


def build_live_message(previews: list[dict[str, Any]], phase: str, sale_mode: str = "auto") -> str:
    preview = previews[0] if previews else {}
    title = str(preview.get("title") or "今晚直播").strip()
    name = str(preview.get("name") or "").strip()
    open_time = format_open_time(preview.get("openTime"))
    time_text = f"，时间是 {open_time}" if open_time else ""
    owner_text = f"{name} " if name else ""
    if sale_mode == "non-sale":
        return "\n".join(
            [
                "📣📣📣直播通知",
                "",
                "亲爱的家人们 🌹🌹🌹",
                "",
                f"🔔 {owner_text}{title}{time_text}。",
                "今天如果不安排卖货，我们只在群里同步直播提醒，不私发打扰大家。",
                "",
                "🙋🙋🙋有任何问题随时联系客服苏苏/小雪/阳阳哟",
                "",
                "💖观看苏丹直播💖",
                "",
                "💖加倍健康幸福💖",
            ]
        )
    if phase == "final":
        return f"{owner_text}{title}{time_text}。直播马上开始，大家有空可以点进来看看。"
    if phase == "link":
        return f"{owner_text}{title}{time_text}。直播入口已经准备好了，方便的话现在就可以进来。"
    return f"{owner_text}{title}{time_text}。今天有直播提醒，别错过。"


def build_live_reminder_content(
    previews: list[dict[str, Any]],
    *,
    phase: str,
    sale_mode: str = "auto",
    copy_mode: str = "template",
    copy_runner: Any | None = None,
    agent_id: str | None = None,
    timeout_seconds: int | None = None,
) -> tuple[str, dict[str, Any]]:
    fallback = build_live_message(previews, phase, sale_mode)
    if copy_mode != "agent":
        return fallback, {"fallbackUsed": False, "copyMode": "template", "sendChannel": "group"}
    preview = previews[0] if previews else {}
    context = {
        "phase": phase,
        "saleMode": sale_mode,
        "preview": preview,
        "styleReference": "参考口吻：亲爱的家人们、直播通知、玫瑰/爱心/小人表情，亲切但不要过度刷屏。",
        "channelRule": "直播提醒默认只发群；非卖货直播必须只发群，不写私发重点客户。",
    }
    content, meta = generate_agent_copy(
        CopyRequest(task="live-reminder", channel="group", fallback=fallback, context=context),
        runner=copy_runner,
        agent_id=agent_id,
        timeout_seconds=timeout_seconds,
    )
    meta["sendChannel"] = "group"
    return content, meta


def build_health_tip_message(topic: str) -> str:
    clean_topic = str(topic or "日常养生").strip() or "日常养生"
    return "\n".join(
        [
            "每日养生不缺席 🌿",
            "",
            f"今天和大家聊聊：{clean_topic}",
            "",
            "1. 饮食尽量温和规律，少一点生冷刺激，给身体留出舒服的节奏。",
            "2. 作息别太晚，睡眠稳了，白天精神和状态都会更好。",
            "3. 黄精熟地这类食养搭配，按平时节奏坚持就好，不要急着加量。",
            "",
            "大家最近更关心哪类养生小问题？可以在群里说说～",
        ]
    )


def build_health_tip_content(
    topic: str,
    previews: list[dict[str, Any]] | None = None,
    *,
    copy_mode: str = "template",
    copy_runner: Any | None = None,
    agent_id: str | None = None,
    timeout_seconds: int | None = None,
    copy_date: Any | None = None,
) -> tuple[str, dict[str, Any]]:
    fallback = build_health_tip_message(topic)
    if copy_mode != "agent":
        return fallback, {"fallbackUsed": False, "copyMode": "template", "sendChannel": "group"}
    daily_context = build_daily_copy_context(live_previews=previews or [], now=copy_date)
    context = {
        "topic": topic,
        "today": daily_context.today,
        "solarTerm": daily_context.solar_term,
        "recentLivePreview": daily_context.live_context,
        "requirement": "围绕当日或昨日直播间核心内容，生成3到5条养生小知识，并带一个互动提问。如果没有直播上下文且 solarTerm 为空，不要编造节气。",
    }
    return generate_agent_copy(
        CopyRequest(task="health-tip", channel="group", fallback=fallback, context=context),
        runner=copy_runner,
        agent_id=agent_id,
        timeout_seconds=timeout_seconds,
    )


def infer_health_tip_topic(previews: list[dict[str, Any]], override: str | None = None) -> str:
    if override:
        return override.strip()
    preview = previews[0] if previews else {}
    for key in ("title", "name", "summary", "content"):
        value = str(preview.get(key) or "").strip()
        if value:
            return value[:40]
    return "日常养生"


def normalize_health_tip_topic(value: str) -> str:
    text = strip_html(value)
    text = re.sub(r"^[#\-*\d.、\s]+", "", text)
    first_line = text.splitlines()[0].strip() if text else ""
    return first_line[:40] or "日常养生"


def plan_health_tip_topic(
    previews: list[dict[str, Any]],
    override: str | None = None,
    *,
    copy_runner: Any | None = None,
    agent_id: str | None = None,
    timeout_seconds: int | None = None,
    copy_date: Any | None = None,
) -> tuple[str, dict[str, Any]]:
    if override:
        return override.strip(), {"source": "manual", "copyMode": "manual"}

    live_context = compact_live_context(previews)
    fallback = normalize_health_tip_topic(infer_health_tip_topic(previews))
    copy_day = parse_copy_date(copy_date)
    solar_term = solar_term_for_day(copy_day)
    if not live_context:
        if solar_term:
            return f"{solar_term}时节养生", {
                "source": "solar-term",
                "copyMode": "template",
                "solarTerm": solar_term,
                "today": copy_day.isoformat(),
            }
        return fallback, {
            "source": "fallback",
            "copyMode": "template",
            "solarTerm": "",
            "today": copy_day.isoformat(),
        }
    content, meta = generate_agent_copy(
        CopyRequest(
            task="health-topic-plan",
            channel="internal",
            fallback=fallback,
            context={
                "today": copy_day.isoformat(),
                "solarTerm": solar_term,
                "recentLiveContext": live_context,
                "examples": ["秋冬滋补避坑指南", "黄精熟地搭配滋补食材技巧", "八段锦入门小提醒"],
                "requirement": "根据当日或昨日直播间核心内容，确定一个适合群发的养生小知识主题。只输出短主题，不要写完整文案；没有依据时不要编造节气。",
            },
            tone="运营策划，准确提炼直播核心内容",
        ),
        runner=copy_runner,
        agent_id=agent_id,
        timeout_seconds=timeout_seconds,
    )
    topic = normalize_health_tip_topic(content)
    meta["source"] = "agent" if not meta.get("fallbackUsed") else "fallback"
    meta["copyMode"] = "agent"
    meta["liveContextCount"] = len(live_context)
    meta["solarTerm"] = solar_term
    meta["today"] = copy_day.isoformat()
    return topic, meta


def build_private_greeting_content(args: argparse.Namespace, copy_runner: Any | None = None) -> tuple[str, dict[str, Any]]:
    if args.content:
        return args.content, {"copyMode": "manual", "sendChannel": "private"}
    if args.content_file:
        return Path(args.content_file).read_text(encoding="utf-8").strip(), {"copyMode": "manual-file", "sendChannel": "private"}

    daily_context = build_daily_copy_context(
        weather_text=getattr(args, "weather_text", "") or "",
        holiday_text=getattr(args, "holiday_text", "") or "",
        now=getattr(args, "date", None),
    )
    fragments = ["早安～"]
    if daily_context.weather_text:
        fragments.append(daily_context.weather_text)
    if daily_context.holiday_text:
        fragments.append(daily_context.holiday_text)
    fragments.append("今天也记得照顾好自己。")
    fragments.append("黄精熟地按平时节奏坚持就好，有不舒服或疑问随时找我。")
    fallback = "".join(fragments)
    if getattr(args, "copy_mode", "template") != "agent":
        return fallback, {"fallbackUsed": False, "copyMode": "template", "sendChannel": "private"}
    return generate_agent_copy(
        CopyRequest(
            task="private-greeting",
            channel="private",
            fallback=fallback,
            context={
                "today": daily_context.today,
                "weatherText": daily_context.weather_text,
                "solarTerm": daily_context.solar_term,
                "holidayText": daily_context.holiday_text,
                "productFocus": daily_context.product_focus,
                "styleReferences": PRIVATE_GREETING_STYLE_REFERENCES,
                "requirement": "生成早安问候或节气祝福，结合天气/节气，轻轻提醒黄精怀熟地黄和好视力眼贴等日常养护，不要过度推销。",
            },
        ),
        runner=copy_runner,
        agent_id=getattr(args, "copywriter_agent_id", None),
        timeout_seconds=getattr(args, "copywriter_timeout_seconds", None),
    )


def build_private_greeting(args: argparse.Namespace, copy_runner: Any | None = None) -> str:
    content, _meta = build_private_greeting_content(args, copy_runner)
    return content


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
    if args.content:
        content = args.content
        copy_meta = {"copyMode": "manual", "sendChannel": "group"}
    else:
        content, copy_meta = build_vegetable_content(
            products,
            copy_mode=args.copy_mode,
            agent_id=args.copywriter_agent_id,
            timeout_seconds=args.copywriter_timeout_seconds,
        )
    targets = group_targets(client, args.group_limit, args.page_size)
    emit_plan(
        {
            "task": "vegetable-push",
            "mode": "execute" if args.execute else "dry-run",
            "copy": copy_meta,
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
    if args.content:
        content = args.content
        copy_meta = {"copyMode": "manual", "sendChannel": "group"}
    else:
        content, copy_meta = build_live_reminder_content(
            previews,
            phase=args.phase,
            sale_mode=args.sale_mode,
            copy_mode=args.copy_mode,
            agent_id=args.copywriter_agent_id,
            timeout_seconds=args.copywriter_timeout_seconds,
        )
    targets = group_targets(client, args.group_limit, args.page_size)
    emit_plan(
        {
            "task": "live-reminder",
            "mode": "execute" if args.execute else "dry-run",
            "phase": args.phase,
            "saleMode": args.sale_mode,
            "copy": copy_meta,
            "previewCount": len(previews),
            "targetCount": len(targets),
            "messages": execute_group_plan(client, targets, content, args.execute),
        }
    )


def command_health_tip(args: argparse.Namespace) -> None:
    client = create_client()
    payload = client.get("yugao-list")
    require_success(payload, "yugao-list")
    previews = records(payload)
    topic_plan: dict[str, Any] = {"source": "manual" if args.topic else "template", "copyMode": "template"}
    topic = infer_health_tip_topic(previews, args.topic)
    if args.content:
        content = args.content
        copy_meta = {"copyMode": "manual", "sendChannel": "group"}
    else:
        if args.copy_mode == "agent":
            topic, topic_plan = plan_health_tip_topic(
                previews,
                args.topic,
                agent_id=args.copywriter_agent_id,
                timeout_seconds=args.copywriter_timeout_seconds,
                copy_date=args.date,
            )
        content, copy_meta = build_health_tip_content(
            topic,
            previews,
            copy_mode=args.copy_mode,
            agent_id=args.copywriter_agent_id,
            timeout_seconds=args.copywriter_timeout_seconds,
            copy_date=args.date,
        )
    targets = group_targets(client, args.group_limit, args.page_size)
    emit_plan(
        {
            "task": "health-tip",
            "mode": "execute" if args.execute else "dry-run",
            "topic": topic,
            "topicPlan": topic_plan,
            "copy": copy_meta,
            "previewCount": len(previews),
            "targetCount": len(targets),
            "messages": execute_group_plan(client, targets, content, args.execute),
        }
    )


def command_generate_copy(args: argparse.Namespace) -> None:
    client = create_client() if args.task in {"live-reminder", "vegetable-push", "health-tip"} else None
    previews: list[dict[str, Any]] = []
    products: list[dict[str, Any]] = []
    if client and args.task in {"live-reminder", "health-tip"}:
        payload = client.get("yugao-list")
        require_success(payload, "yugao-list")
        previews = records(payload)
    if client and args.task == "vegetable-push":
        payload = client.get("product-list", {"name": args.keyword})
        require_success(payload, "product-list")
        products = records(payload)

    if args.task == "private-greeting":
        greeting_args = argparse.Namespace(
            content=None,
            content_file=None,
            weather_text=args.weather_text,
            holiday_text=args.holiday_text,
            copy_mode=args.copy_mode,
            copywriter_agent_id=args.copywriter_agent_id,
            copywriter_timeout_seconds=args.copywriter_timeout_seconds,
            date=args.date,
        )
        content, copy_meta = build_private_greeting_content(greeting_args)
    elif args.task == "live-reminder":
        content, copy_meta = build_live_reminder_content(
            previews,
            phase=args.phase,
            sale_mode=args.sale_mode,
            copy_mode=args.copy_mode,
            agent_id=args.copywriter_agent_id,
            timeout_seconds=args.copywriter_timeout_seconds,
        )
    elif args.task == "health-tip":
        topic, topic_plan = (
            plan_health_tip_topic(
                previews,
                args.topic,
                agent_id=args.copywriter_agent_id,
                timeout_seconds=args.copywriter_timeout_seconds,
                copy_date=args.date,
            )
            if args.copy_mode == "agent"
            else (infer_health_tip_topic(previews, args.topic), {"source": "manual" if args.topic else "template"})
        )
        content, copy_meta = build_health_tip_content(
            topic,
            previews,
            copy_mode=args.copy_mode,
            agent_id=args.copywriter_agent_id,
            timeout_seconds=args.copywriter_timeout_seconds,
            copy_date=args.date,
        )
        copy_meta["topicPlan"] = topic_plan
    elif args.task == "vegetable-push":
        content, copy_meta = build_vegetable_content(
            products,
            copy_mode=args.copy_mode,
            agent_id=args.copywriter_agent_id,
            timeout_seconds=args.copywriter_timeout_seconds,
        )
    else:
        raise RuntimeError(f"unsupported copy task: {args.task}")

    emit_plan({"task": "generate-copy", "copyTask": args.task, "copy": copy_meta, "content": content})


def command_private_greeting(args: argparse.Namespace) -> None:
    client = create_client()
    content, copy_meta = build_private_greeting_content(args)
    targets = explicit_member_targets(args.mobile, args.mobiles) or member_targets(client, args.member_limit, args.page_size)
    emit_plan(
        {
            "task": "private-greeting",
            "mode": "execute" if args.execute else "dry-run",
            "copy": copy_meta,
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


def add_copywriter_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--copy-mode",
        choices=["template", "agent"],
        default=os.environ.get("SUDAN_COPY_MODE", "template"),
        help="Use fixed templates or ask the local OpenClaw agent to generate copy.",
    )
    parser.add_argument(
        "--copywriter-agent-id",
        default=os.environ.get("SUDAN_COPYWRITER_AGENT_ID", DEFAULT_COPYWRITER_AGENT_ID),
        help="OpenClaw agent id used when --copy-mode agent.",
    )
    parser.add_argument(
        "--copywriter-timeout-seconds",
        type=int,
        default=int(os.environ.get("SUDAN_COPYWRITER_TIMEOUT_SECONDS", DEFAULT_COPYWRITER_TIMEOUT_SECONDS)),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sudan customer-service daily automation helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    api_check = subparsers.add_parser("api-check", help="Check read-only API availability.")
    api_check.add_argument("--product-keyword", default="蔬菜")
    api_check.set_defaults(func=command_api_check)

    vegetable = subparsers.add_parser("vegetable-push", help="Build/send daily vegetable group push.")
    add_common_send_flags(vegetable)
    add_copywriter_flags(vegetable)
    vegetable.add_argument("--keyword", default="蔬菜")
    vegetable.add_argument("--group-limit", type=int, default=3, help="Limit target groups. Use 0 for all groups.")
    vegetable.add_argument("--content", help="Override generated message content.")
    vegetable.set_defaults(func=lambda args: normalize_limits(args, "group_limit", command_vegetable_push))

    live = subparsers.add_parser("live-reminder", help="Build/send live preview group reminder.")
    add_common_send_flags(live)
    add_copywriter_flags(live)
    live.add_argument("--phase", choices=["pre", "final", "link"], default="pre")
    live.add_argument("--sale-mode", choices=["auto", "sale", "non-sale"], default="auto")
    live.add_argument("--group-limit", type=int, default=3, help="Limit target groups. Use 0 for all groups.")
    live.add_argument("--content", help="Override generated message content.")
    live.set_defaults(func=lambda args: normalize_limits(args, "group_limit", command_live_reminder))

    health_tip = subparsers.add_parser("health-tip", help="Build/send a group health tip around live content.")
    add_common_send_flags(health_tip)
    add_copywriter_flags(health_tip)
    health_tip.add_argument("--topic", help="Override the health tip topic.")
    health_tip.add_argument("--date", help="Copy date in YYYY-MM-DD, defaults to today in China timezone.")
    health_tip.add_argument("--group-limit", type=int, default=3, help="Limit target groups. Use 0 for all groups.")
    health_tip.add_argument("--content", help="Override generated message content.")
    health_tip.set_defaults(func=lambda args: normalize_limits(args, "group_limit", command_health_tip))

    greeting = subparsers.add_parser("private-greeting", help="Build/send private morning greetings.")
    add_common_send_flags(greeting)
    add_copywriter_flags(greeting)
    greeting.add_argument("--member-limit", type=int, default=10, help="Limit target members. Use 0 for all members.")
    greeting.add_argument("--mobile", action="append", help="Exact mobile target. Can be used multiple times.")
    greeting.add_argument("--mobiles", help="Comma separated exact mobile targets.")
    greeting.add_argument("--weather-text", help="Weather text from OpenClaw search or external source.")
    greeting.add_argument("--holiday-text", help="Holiday/solar-term text from OpenClaw search or external source.")
    greeting.add_argument("--date", help="Copy date in YYYY-MM-DD, defaults to today in China timezone.")
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

    generate_copy = subparsers.add_parser("generate-copy", help="Generate one automation copy draft without sending.")
    add_copywriter_flags(generate_copy)
    generate_copy.set_defaults(copy_mode="agent")
    generate_copy.add_argument(
        "--task",
        choices=["private-greeting", "live-reminder", "health-tip", "vegetable-push"],
        required=True,
    )
    generate_copy.add_argument("--phase", choices=["pre", "final", "link"], default="pre")
    generate_copy.add_argument("--sale-mode", choices=["auto", "sale", "non-sale"], default="auto")
    generate_copy.add_argument("--weather-text", default="")
    generate_copy.add_argument("--holiday-text", default="")
    generate_copy.add_argument("--date", help="Copy date in YYYY-MM-DD, defaults to today in China timezone.")
    generate_copy.add_argument("--topic")
    generate_copy.add_argument("--keyword", default="蔬菜")
    generate_copy.set_defaults(func=command_generate_copy)

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
