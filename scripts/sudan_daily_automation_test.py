#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import argparse
import sys
import unittest
from datetime import date
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).with_name("sudan_daily_automation.py")
SPEC = importlib.util.spec_from_file_location("sudan_daily_automation", SCRIPT_PATH)
sudan_daily_automation = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = sudan_daily_automation
SPEC.loader.exec_module(sudan_daily_automation)


class FakeClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def get(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.action = action
        self.params = params
        return self.payload


class GroupTargetTest(unittest.TestCase):
    def test_group_targets_use_numeric_id_for_send_and_keep_chatroom_gid(self) -> None:
        client = FakeClient(
            {
                "code": 200,
                "data": {
                    "items": [
                        {
                            "id": "2047585234834935810",
                            "gid": "53220657641@chatroom",
                            "name": "测试",
                        }
                    ]
                },
            }
        )

        targets = sudan_daily_automation.group_targets(client, limit=1, page_size=20)

        self.assertEqual(targets[0]["id"], "2047585234834935810")
        self.assertEqual(targets[0]["gid"], "53220657641@chatroom")


class ExplicitMemberTargetTest(unittest.TestCase):
    def test_explicit_member_targets_use_only_requested_mobiles(self) -> None:
        targets = sudan_daily_automation.explicit_member_targets(
            ["18256819124", " 13002527669 "],
            "18256819124,,",
        )

        self.assertEqual(
            targets,
            [
                {"mobile": "18256819124", "name": "", "userId": None, "raw": {"mobile": "18256819124"}},
                {"mobile": "13002527669", "name": "", "userId": None, "raw": {"mobile": "13002527669"}},
            ],
        )


class AgentCopywriterTest(unittest.TestCase):
    def test_default_copywriter_agent_is_primary_openclaw_agent(self) -> None:
        self.assertEqual(sudan_daily_automation.DEFAULT_COPYWRITER_AGENT_ID, "main")

    def test_copywriter_agent_uses_fresh_session_for_each_request(self) -> None:
        calls: list[list[str]] = []
        original_run = sudan_daily_automation.subprocess.run
        original_resolve = sudan_daily_automation.resolve_openclaw_bin

        class Completed:
            returncode = 0
            stdout = '{"content":"早安","riskLevel":"low"}'
            stderr = ""

        def fake_run(args: list[str], **_kwargs: Any) -> Completed:
            calls.append(args)
            return Completed()

        sudan_daily_automation.subprocess.run = fake_run
        sudan_daily_automation.resolve_openclaw_bin = lambda _value: "openclaw"
        try:
            sudan_daily_automation.run_copywriter_agent("first", agent_id="main", timeout_seconds=1)
            sudan_daily_automation.run_copywriter_agent("second", agent_id="main", timeout_seconds=1)
        finally:
            sudan_daily_automation.subprocess.run = original_run
            sudan_daily_automation.resolve_openclaw_bin = original_resolve

        session_ids = [args[args.index("--session-id") + 1] for args in calls]
        self.assertNotEqual(session_ids[0], session_ids[1])

    def test_parse_agent_copy_extracts_json_from_markdown_fence(self) -> None:
        result = sudan_daily_automation.parse_agent_copy_output(
            '```json\n{"content":"每日养生不缺席 🌿","riskLevel":"low","sendChannel":"group"}\n```'
        )

        self.assertEqual(result["content"], "每日养生不缺席 🌿")
        self.assertEqual(result["sendChannel"], "group")

    def test_validate_generated_copy_rejects_medical_claims(self) -> None:
        with self.assertRaises(ValueError):
            sudan_daily_automation.validate_generated_copy("这个方法保证有效，可以根治不适。")

    def test_generate_copy_uses_fallback_when_agent_fails(self) -> None:
        request = sudan_daily_automation.CopyRequest(
            task="private-greeting",
            channel="private",
            fallback="早安～今天也记得照顾好自己。",
            context={"weatherText": "今日谷雨。"},
        )

        def failing_runner(_prompt: str) -> str:
            raise RuntimeError("agent unavailable")

        content, meta = sudan_daily_automation.generate_agent_copy(request, runner=failing_runner)

        self.assertEqual(content, "早安～今天也记得照顾好自己。")
        self.assertEqual(meta["fallbackUsed"], True)

    def test_generate_copy_retries_transient_agent_failure(self) -> None:
        request = sudan_daily_automation.CopyRequest(
            task="private-greeting",
            channel="private",
            fallback="早安～今天也记得照顾好自己。",
            context={"weatherText": ""},
        )
        calls = 0

        def flaky_runner(_prompt: str) -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("temporary gateway failure")
            return '{"content":"早安，今天换个轻松问候。","riskLevel":"low","sendChannel":"private"}'

        content, meta = sudan_daily_automation.generate_agent_copy(request, runner=flaky_runner, attempts=2)

        self.assertEqual(content, "早安，今天换个轻松问候。")
        self.assertEqual(meta["fallbackUsed"], False)
        self.assertEqual(meta["attempts"], 2)

    def test_resolve_openclaw_bin_finds_pnpm_global_candidate(self) -> None:
        original_which = sudan_daily_automation.shutil.which
        original_glob = sudan_daily_automation.glob.glob
        original_exists = sudan_daily_automation.Path.exists

        def fake_exists(path: Path) -> bool:
            normalized = str(path).replace("\\", "/")
            return normalized.endswith("/root/.local/share/pnpm/openclaw")

        sudan_daily_automation.shutil.which = lambda _value: None
        sudan_daily_automation.glob.glob = lambda _pattern: []
        sudan_daily_automation.Path.exists = fake_exists
        try:
            resolved = sudan_daily_automation.resolve_openclaw_bin("openclaw")
        finally:
            sudan_daily_automation.shutil.which = original_which
            sudan_daily_automation.glob.glob = original_glob
            sudan_daily_automation.Path.exists = original_exists

        self.assertEqual(resolved, "/root/.local/share/pnpm/openclaw")


class CopyModeIntegrationTest(unittest.TestCase):
    def test_private_greeting_agent_copy_uses_weather_and_holiday_context(self) -> None:
        args = argparse.Namespace(
            content=None,
            content_file=None,
            weather_text="今日谷雨，雨生百谷。",
            holiday_text="谷雨节气，适合温润养护。",
            copy_mode="agent",
        )

        content = sudan_daily_automation.build_private_greeting(
            args,
            copy_runner=lambda _prompt: '{"content":"今日谷雨，记得温润养护 🌿","riskLevel":"low"}',
        )

        self.assertIn("谷雨", content)
        self.assertIn("🌿", content)

    def test_non_sale_live_reminder_stays_group_copy(self) -> None:
        content, meta = sudan_daily_automation.build_live_reminder_content(
            [{"title": "今晚直播暂停一天", "name": "苏丹老师"}],
            phase="link",
            sale_mode="non-sale",
            copy_mode="agent",
            copy_runner=lambda _prompt: (
                '{"content":"📣📣📣直播通知\\n亲爱的家人们 🌹🌹🌹\\n今晚直播不卖货，只在群里提醒大家。",'
                '"riskLevel":"low","sendChannel":"group"}'
            ),
        )

        self.assertIn("直播通知", content)
        self.assertEqual(meta["sendChannel"], "group")


class HealthTipTest(unittest.TestCase):
    def test_health_tip_fallback_has_points_and_question(self) -> None:
        content = sudan_daily_automation.build_health_tip_message("秋冬滋补")

        self.assertIn("1.", content)
        self.assertIn("大家", content)
        self.assertIn("？", content)


class DailyCopyContextTest(unittest.TestCase):
    def test_daily_copy_context_adds_solar_term_when_date_matches(self) -> None:
        context = sudan_daily_automation.build_daily_copy_context(
            weather_text="今日阴，注意添衣。",
            holiday_text="",
            now=date(2026, 12, 21),
        )

        self.assertEqual(context.solar_term, "冬至")
        self.assertIn("冬至", context.holiday_text)

    def test_private_greeting_agent_context_includes_solar_term_and_reference_style(self) -> None:
        args = argparse.Namespace(
            content=None,
            content_file=None,
            weather_text="今日谷雨，雨生百谷。",
            holiday_text="",
            copy_mode="agent",
            copywriter_agent_id=None,
            copywriter_timeout_seconds=None,
            date="2026-04-20",
        )
        seen: dict[str, str] = {}

        def runner(prompt: str) -> str:
            seen["prompt"] = prompt
            return '{"content":"今日谷雨，记得温润养护 🌿","riskLevel":"low"}'

        content, meta = sudan_daily_automation.build_private_greeting_content(args, copy_runner=runner)

        self.assertIn("谷雨", content)
        self.assertEqual(meta["fallbackUsed"], False)
        self.assertIn("谷雨", seen["prompt"])
        self.assertIn("每日养生不缺席", seen["prompt"])
        self.assertIn("好视力眼贴", seen["prompt"])
        self.assertIn("黄精怀熟地黄", seen["prompt"])

    def test_private_greeting_agent_context_changes_by_date(self) -> None:
        prompts: list[str] = []

        def runner(prompt: str) -> str:
            prompts.append(prompt)
            return '{"content":"早安，今天换一种轻松问候 🌿","riskLevel":"low"}'

        for copy_date in ("2026-04-28", "2026-04-29"):
            args = argparse.Namespace(
                content=None,
                content_file=None,
                weather_text="",
                holiday_text="",
                copy_mode="agent",
                copywriter_agent_id=None,
                copywriter_timeout_seconds=None,
                date=copy_date,
            )
            sudan_daily_automation.build_private_greeting_content(args, copy_runner=runner)

        self.assertNotEqual(prompts[0], prompts[1])
        self.assertIn("dailyVariation", prompts[0])
        self.assertIn("不要复用前一天", prompts[0])

    def test_private_greeting_execute_does_not_send_template_when_agent_fails(self) -> None:
        original_create_client = sudan_daily_automation.create_client
        original_run = sudan_daily_automation.run_copywriter_agent
        original_send_chat = sudan_daily_automation.send_chat
        sent: list[str] = []

        sudan_daily_automation.create_client = lambda: FakeClient({"code": 200, "data": []})
        sudan_daily_automation.run_copywriter_agent = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("agent unavailable")
        )
        sudan_daily_automation.send_chat = lambda _client, mobile, _content: sent.append(mobile) or {"code": 200}
        args = argparse.Namespace(
            content=None,
            content_file=None,
            weather_text="",
            holiday_text="",
            copy_mode="agent",
            copywriter_agent_id=None,
            copywriter_timeout_seconds=None,
            date="2026-04-29",
            mobile=["13002527669"],
            mobiles=None,
            member_limit=10,
            page_size=20,
            execute=True,
            allow_fallback_send=False,
        )
        try:
            with self.assertRaises(RuntimeError):
                sudan_daily_automation.command_private_greeting(args)
        finally:
            sudan_daily_automation.create_client = original_create_client
            sudan_daily_automation.run_copywriter_agent = original_run
            sudan_daily_automation.send_chat = original_send_chat

        self.assertEqual(sent, [])


class HealthTopicPlannerTest(unittest.TestCase):
    def test_health_tip_topic_planner_uses_agent_with_live_context(self) -> None:
        previews = [
            {
                "title": "今晚秋冬滋补专场",
                "summary": "重点讲黄精熟地搭配滋补食材技巧",
            }
        ]
        seen: dict[str, str] = {}

        def runner(prompt: str) -> str:
            seen["prompt"] = prompt
            return '{"content":"秋冬滋补避坑指南","riskLevel":"low"}'

        topic, meta = sudan_daily_automation.plan_health_tip_topic(previews, copy_runner=runner)

        self.assertEqual(topic, "秋冬滋补避坑指南")
        self.assertEqual(meta["source"], "agent")
        self.assertIn("秋冬滋补", seen["prompt"])
        self.assertIn("黄精熟地", seen["prompt"])

    def test_health_tip_topic_planner_uses_manual_override(self) -> None:
        def runner(_prompt: str) -> str:
            raise AssertionError("manual topic should not call OpenClaw")

        topic, meta = sudan_daily_automation.plan_health_tip_topic(
            [{"title": "今晚秋冬滋补专场"}],
            override="八段锦入门",
            copy_runner=runner,
        )

        self.assertEqual(topic, "八段锦入门")
        self.assertEqual(meta["source"], "manual")

    def test_health_tip_topic_planner_does_not_invent_topic_without_context(self) -> None:
        def runner(_prompt: str) -> str:
            raise AssertionError("empty live context should not ask OpenClaw to invent a topic")

        topic, meta = sudan_daily_automation.plan_health_tip_topic(
            [],
            copy_runner=runner,
            copy_date=date(2026, 4, 28),
        )

        self.assertEqual(topic, "日常养生")
        self.assertEqual(meta["source"], "fallback")

    def test_health_tip_topic_planner_can_use_solar_term_without_live_context(self) -> None:
        def runner(_prompt: str) -> str:
            raise AssertionError("solar-term fallback should not need OpenClaw topic planning")

        topic, meta = sudan_daily_automation.plan_health_tip_topic(
            [],
            copy_runner=runner,
            copy_date=date(2026, 12, 21),
        )

        self.assertEqual(topic, "冬至时节养生")
        self.assertEqual(meta["source"], "solar-term")


if __name__ == "__main__":
    unittest.main()
