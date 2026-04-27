#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
