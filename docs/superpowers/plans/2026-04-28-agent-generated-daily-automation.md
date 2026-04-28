# Agent Generated Daily Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Sudan daily automation call the server agent to generate context-aware copy for greetings, health tips, and live reminders while keeping scripts responsible for recipients, safety checks, dry-run behavior, and logging.

**Architecture:** Keep the existing `scripts/sudan_daily_automation.py` entrypoint. Add a focused copywriter layer inside that script so cron commands can choose `--copy-mode template` or `--copy-mode agent`; the copywriter builds structured prompts, calls OpenClaw, parses JSON, checks safety, and falls back to templates when needed. Add `health-tip` and `generate-copy` commands without changing send APIs.

**Tech Stack:** Python 3 standard library, existing Metast MCP HTTP endpoints, existing OpenClaw CLI command shape, `unittest`.

---

### Task 1: Copywriter Core

**Files:**
- Modify: `scripts/sudan_daily_automation.py`
- Test: `scripts/sudan_daily_automation_test.py`

- [ ] **Step 1: Write failing tests**

Add tests for JSON extraction, blocked health claims, and fallback behavior:

```python
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
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
python scripts/sudan_daily_automation_test.py
```

Expected: failures for missing `parse_agent_copy_output`, `CopyRequest`, and `generate_agent_copy`.

- [ ] **Step 3: Implement minimal copywriter core**

Add `CopyRequest`, prompt builder, JSON parser, medical-claim validator, and `generate_agent_copy`.

- [ ] **Step 4: Verify tests pass**

Run:

```bash
python scripts/sudan_daily_automation_test.py
python -m py_compile scripts/sudan_daily_automation.py scripts/sudan_daily_automation_test.py
```

Expected: all tests pass.

### Task 2: Wire Agent Copy Into Existing Commands

**Files:**
- Modify: `scripts/sudan_daily_automation.py`
- Test: `scripts/sudan_daily_automation_test.py`

- [ ] **Step 1: Write failing tests**

Add tests for `private-greeting` and `live-reminder` content selection:

```python
class CopyModeIntegrationTest(unittest.TestCase):
    def test_private_greeting_agent_copy_uses_weather_and_holiday_context(self) -> None:
        args = argparse.Namespace(
            content=None,
            content_file=None,
            weather_text="今日谷雨，雨生百谷。",
            holiday_text="谷雨节气，适合温润养护。",
            copy_mode="agent",
        )
        content = sudan_daily_automation.build_private_greeting(args, copy_runner=lambda _prompt: '{"content":"今日谷雨，记得温润养护 🌿","riskLevel":"low"}')
        self.assertIn("谷雨", content)
        self.assertIn("🌿", content)

    def test_non_sale_live_reminder_stays_group_copy(self) -> None:
        content, meta = sudan_daily_automation.build_live_reminder_content(
            [{"title": "今晚直播暂停一天", "name": "苏丹老师"}],
            phase="link",
            sale_mode="non-sale",
            copy_mode="agent",
            copy_runner=lambda _prompt: '{"content":"📣📣📣直播通知\\n亲爱的家人们 🌹🌹🌹\\n今晚直播不卖货，只在群里提醒大家。","riskLevel":"low","sendChannel":"group"}',
        )
        self.assertIn("直播通知", content)
        self.assertEqual(meta["sendChannel"], "group")
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
python scripts/sudan_daily_automation_test.py
```

Expected: missing args/functions until integration exists.

- [ ] **Step 3: Implement integration**

Add common CLI flags:

```text
--copy-mode template|agent
--copywriter-agent-id sudan-main
--copywriter-timeout-seconds 90
```

Add `--sale-mode auto|sale|non-sale` to `live-reminder`.

- [ ] **Step 4: Verify tests pass**

Run:

```bash
python scripts/sudan_daily_automation_test.py
python -m py_compile scripts/sudan_daily_automation.py scripts/sudan_daily_automation_test.py
```

Expected: all tests pass.

### Task 3: Add Health Tip and Generate-Copy Commands

**Files:**
- Modify: `scripts/sudan_daily_automation.py`
- Modify: `internal-maintenance/AUTOMATION_WORKFLOW.md`
- Modify: `internal-maintenance/AI客服每日工作流程-任务完成清单.md`
- Test: `scripts/sudan_daily_automation_test.py`

- [ ] **Step 1: Write failing tests**

Add tests that health tips contain 3-5 points and interactive question:

```python
class HealthTipTest(unittest.TestCase):
    def test_health_tip_fallback_has_points_and_question(self) -> None:
        content = sudan_daily_automation.build_health_tip_message("秋冬滋补")
        self.assertIn("1.", content)
        self.assertIn("大家", content)
        self.assertIn("？", content)
```

- [ ] **Step 2: Implement commands**

Add:

```bash
python scripts/sudan_daily_automation.py generate-copy --task live-reminder --copy-mode agent
python scripts/sudan_daily_automation.py health-tip --topic 秋冬滋补 --copy-mode agent --group-limit 1
```

`health-tip` must send groups only and must keep dry-run unless `--execute` is present.

- [ ] **Step 3: Update docs**

Document:

- Copy mode defaults to `template`.
- Agent mode can be enabled per cron line.
- Non-sale live reminders remain group-only.
- Health content is checked against blocked medical claims.

- [ ] **Step 4: Verify**

Run:

```bash
python scripts/sudan_daily_automation_test.py
python -m py_compile scripts/sudan_daily_automation.py scripts/sudan_daily_automation_test.py
```

Expected: all tests pass.

### Task 4: PR and Server Rollout

**Files:**
- Modify only after merge on server:
  - `/root/Sudan`
  - root crontab
  - `/var/log/sudan-automation`
- Local record:
  - `docs/server-change-log.md`

- [ ] **Step 1: Run local verification**

```bash
python scripts/sudan_daily_automation_test.py
python -m py_compile scripts/sudan_daily_automation.py scripts/sudan_daily_automation_test.py
```

- [ ] **Step 2: Commit, push, open PR**

Use branch `codex/agent-generated-daily-automation`.

- [ ] **Step 3: After PR merge, server pulls from GitHub**

Do not hot-edit project code on the server.

- [ ] **Step 4: Server dry-run**

Run all new agent copy commands in dry-run first.

- [ ] **Step 5: Ask before changing cron**

Changing root crontab is a direct server configuration change. Confirm with the user before switching cron to `--copy-mode agent` or adding the new `health-tip` schedule.
