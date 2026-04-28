#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import argparse
import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()
