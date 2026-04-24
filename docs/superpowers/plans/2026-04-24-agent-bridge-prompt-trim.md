# Agent Bridge Prompt Trim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove repeated persona emphasis from the bridge-layer prompt, and make the first bridge instruction explicitly advertise the `metast-mcp` skill.

**Architecture:** Keep the generated system prompt as the single persona source, while reshaping `buildAgentMessage(...)` into a light runtime-guidance layer. Update protocol tests to lock the new prompt shape in place before changing production code.

**Tech Stack:** Node.js, built-in `node:test`, PowerShell for local verification

---

### Task 1: Back Up The Existing Bridge File

**Files:**
- Create: `node-services/agent-bridge/src/server.js.bak`
- Read: `node-services/agent-bridge/src/server.js`

- [ ] **Step 1: Copy the current bridge implementation**

```powershell
Copy-Item -LiteralPath "D:\Study\codeXprojection\苏丹小龙虾\node-services\agent-bridge\src\server.js" -Destination "D:\Study\codeXprojection\苏丹小龙虾\node-services\agent-bridge\src\server.js.bak"
```

- [ ] **Step 2: Verify the backup exists**

Run: `Get-Item "D:\Study\codeXprojection\苏丹小龙虾\node-services\agent-bridge\src\server.js.bak" | Select-Object FullName,Length,LastWriteTime`
Expected: one file record for `server.js.bak`

### Task 2: Lock In The New Prompt Contract With Tests

**Files:**
- Modify: `node-services/agent-bridge/test/protocol.test.js`
- Test: `node-services/agent-bridge/test/protocol.test.js`

- [ ] **Step 1: Add a failing test for the new bridge prompt wording**

```js
test("buildAgentMessage starts with metast-mcp guidance and drops repeated persona wording", () => {
  const message = buildAgentMessage({
    stylePrompt: "补充上下文",
    userMessage: "查一下订单",
    history: [{ role: "user", text: "你好" }],
    knowledgeHits: [],
  });

  assert.equal(
    message.startsWith("当前客服可使用的 skill 为 `metast-mcp`。遇到实时商品、快递、订单查询时优先使用它。"),
    true
  );
  assert.equal(message.includes("你必须优先遵守下方“苏丹人格与回复规则”"), false);
  assert.equal(message.includes("优先使用 sudan skill 里的人格、语气、承接方式来回复"), false);
});
```

- [ ] **Step 2: Run the targeted test and confirm it fails**

Run: `node --test test/protocol.test.js`
Expected: FAIL because `buildAgentMessage` is not yet exported or not yet producing the new wording

### Task 3: Implement The Prompt Reshape

**Files:**
- Modify: `node-services/agent-bridge/src/server.js`

- [ ] **Step 1: Export `buildAgentMessage` for test coverage**

```js
module.exports = {
  buildAgentMessage,
  buildSessionId,
  createErrorPayload,
  createSuccessPayload,
  extractConversation,
  looksIncompleteMessage,
};
```

- [ ] **Step 2: Rewrite the prompt preamble into runtime guidance**

```js
function buildAgentMessage({ stylePrompt, userMessage, history, knowledgeHits }) {
  return [
    "当前客服可使用的 skill 为 `metast-mcp`。遇到实时商品、快递、订单查询时优先使用它。",
    "以下是桥接层提供的隐藏上下文，请直接回复用户，不要提到“桥接层”“上下文”“资料来源”这类字眼。",
    "回复务必更口语、更短。优先 1 到 3 句话，能短就短。",
    "除非用户明确追问，不要一次讲太多，不要写成长段说明文。",
    "如果知识命中不相关，请忽略，不要硬答。",
    "如果知识不足，请自然兜底并引导人工或进一步描述。",
    "",
    "【补充运行上下文】",
    stylePrompt || "未提供额外补充上下文。",
    "",
    "【最近消息】",
    formatHistory(history),
    "",
    "【命中的知识条目】",
    formatKnowledgeHits(knowledgeHits),
    "",
    "【用户本轮消息】",
    userMessage,
  ].join("\n");
}
```

- [ ] **Step 3: Keep the rest of the bridge flow unchanged**

Run: no code block needed beyond the `buildAgentMessage(...)` rewrite above; do not change queueing, knowledge lookup, or response payload code

### Task 4: Verify The New Behavior

**Files:**
- Test: `node-services/agent-bridge/test/protocol.test.js`

- [ ] **Step 1: Run the targeted test again**

Run: `node --test test/protocol.test.js`
Expected: PASS for the new bridge prompt test

- [ ] **Step 2: Run the full bridge test suite**

Run: `node --test`
Expected: all tests PASS

- [ ] **Step 3: Review the diff for scope**

Run: `git diff -- node-services/agent-bridge/src/server.js node-services/agent-bridge/test/protocol.test.js docs/superpowers/specs/2026-04-24-agent-bridge-prompt-trim-design.md docs/superpowers/plans/2026-04-24-agent-bridge-prompt-trim.md`
Expected: diff only shows the prompt reshape, backup-safe implementation changes, and the new planning docs
