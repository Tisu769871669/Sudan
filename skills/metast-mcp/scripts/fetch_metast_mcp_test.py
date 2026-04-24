#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse


SCRIPT_PATH = Path(__file__).with_name("fetch_metast_mcp.py")
SPEC = importlib.util.spec_from_file_location("fetch_metast_mcp", SCRIPT_PATH)
fetch_metast_mcp = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(fetch_metast_mcp)


class EnvFileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.previous = {
            key: os.environ.get(key)
            for key in ("METAST_MCP_BASE_URL", "METAST_MCP_KEY", "METAST_MCP_SECRET")
        }
        for key in self.previous:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_load_env_file_reads_metast_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env.metast"
            env_path.write_text(
                "\n".join(
                    [
                        "METAST_MCP_BASE_URL=https://example.invalid",
                        "METAST_MCP_KEY=test-key",
                        "METAST_MCP_SECRET=test-secret",
                    ]
                ),
                encoding="utf-8",
            )

            fetch_metast_mcp.load_env_file(env_path)

        self.assertEqual(os.environ["METAST_MCP_BASE_URL"], "https://example.invalid")
        self.assertEqual(os.environ["METAST_MCP_KEY"], "test-key")
        self.assertEqual(os.environ["METAST_MCP_SECRET"], "test-secret")

    def test_load_env_file_keeps_existing_environment_values(self) -> None:
        os.environ["METAST_MCP_KEY"] = "existing-key"
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env.metast"
            env_path.write_text("METAST_MCP_KEY=file-key\n", encoding="utf-8")

            fetch_metast_mcp.load_env_file(env_path)

        self.assertEqual(os.environ["METAST_MCP_KEY"], "existing-key")


class BuildUrlTest(unittest.TestCase):
    def query_for(self, url: str) -> dict[str, list[str]]:
        return parse_qs(urlparse(url).query)

    def test_yugao_list_uses_preview_endpoint_without_required_query(self) -> None:
        url = fetch_metast_mcp.build_url("https://example.invalid", "yugao-list", {})

        self.assertEqual(
            url,
            "https://example.invalid/app-api/mcp/api-mcp/yugaoList",
        )

    def test_member_user_list_uses_page_params(self) -> None:
        url = fetch_metast_mcp.build_url(
            "https://example.invalid",
            "member-user-list",
            {"page_no": 2, "page_size": 50},
        )

        self.assertTrue(
            url.startswith(
                "https://example.invalid/app-api/mcp/api-mcp/memberUserList?"
            )
        )
        self.assertEqual(self.query_for(url), {"pageNo": ["2"], "pageSize": ["50"]})

    def test_member_user_order_list_requires_user_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "--user-id USER_ID"):
            fetch_metast_mcp.build_url(
                "https://example.invalid",
                "member-user-order-list",
                {"page_no": 1, "page_size": 20},
            )

    def test_member_user_order_list_uses_user_id_and_page_params(self) -> None:
        url = fetch_metast_mcp.build_url(
            "https://example.invalid",
            "member-user-order-list",
            {"page_no": 1, "page_size": 20, "user_id": 123},
        )

        self.assertEqual(
            self.query_for(url),
            {"pageNo": ["1"], "pageSize": ["20"], "userId": ["123"]},
        )

    def test_order_user_delivery_requires_order_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "--order-id ORDER_ID"):
            fetch_metast_mcp.build_url(
                "https://example.invalid",
                "order-user-delivery",
                {},
            )

    def test_order_user_delivery_uses_order_id(self) -> None:
        url = fetch_metast_mcp.build_url(
            "https://example.invalid",
            "order-user-delivery",
            {"order_id": 456},
        )

        self.assertEqual(
            url,
            "https://example.invalid/app-api/mcp/api-mcp/orderUserdelivery?orderId=456",
        )

    def test_im_group_list_uses_page_params(self) -> None:
        url = fetch_metast_mcp.build_url(
            "https://example.invalid",
            "im-group-list",
            {"page_no": 3, "page_size": 10},
        )

        self.assertTrue(
            url.startswith("https://example.invalid/prod-api/system/api/im/groupList?")
        )
        self.assertEqual(self.query_for(url), {"pageNo": ["3"], "pageSize": ["10"]})

    def test_send_chat_message_uses_mobile_and_content(self) -> None:
        url = fetch_metast_mcp.build_url(
            "https://example.invalid",
            "send-chat-message",
            {"mobile": "13800000000", "content": "hello"},
        )

        self.assertTrue(
            url.startswith(
                "https://example.invalid/prod-api/system/api/im/sendChatMesage?"
            )
        )
        self.assertEqual(
            self.query_for(url),
            {"mobile": ["13800000000"], "content": ["hello"]},
        )

    def test_send_group_message_requires_group_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "--group-id GROUP_ID"):
            fetch_metast_mcp.build_url(
                "https://example.invalid",
                "send-group-message",
                {"content": "hello"},
            )

    def test_send_group_message_uses_group_id_and_content(self) -> None:
        url = fetch_metast_mcp.build_url(
            "https://example.invalid",
            "send-group-message",
            {"group_id": "test-group", "content": "hello"},
        )

        self.assertTrue(
            url.startswith(
                "https://example.invalid/prod-api/system/api/im/sendGroupMesage?"
            )
        )
        self.assertEqual(
            self.query_for(url),
            {"groupId": ["test-group"], "content": ["hello"]},
        )


if __name__ == "__main__":
    unittest.main()
