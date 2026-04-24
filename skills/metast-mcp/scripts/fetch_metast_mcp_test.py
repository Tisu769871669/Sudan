#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
