const test = require("node:test");
const assert = require("node:assert/strict");
const {
  buildAgentMessage,
  buildSessionId,
  createErrorPayload,
  createSuccessPayload,
  extractConversation,
  looksIncompleteMessage,
} = require("../src/server");

test("extractConversation accepts conversation_id and user_id", () => {
  const result = extractConversation({
    conversation_id: "session_001",
    user_id: "user_001",
    content: "你好",
  });

  assert.equal(result.conversationId, "session_001");
  assert.equal(result.userId, "user_001");
  assert.equal(result.userMessage, "你好");
});

test("buildSessionId matches public bridge format", () => {
  assert.equal(buildSessionId("snowchuang", "session_001"), "bridge_snowchuang_session_001");
});

test("createSuccessPayload matches external response schema", () => {
  const payload = createSuccessPayload({
    agentId: "main",
    conversationId: "session_001",
    userId: "",
    reply: "你好",
    sessionId: "bridge_main_session_001",
    traceId: "trace_001",
  });

  assert.deepEqual(payload, {
    ok: true,
    agent_id: "main",
    conversation_id: "session_001",
    user_id: "",
    reply: "你好",
    session_id: "bridge_main_session_001",
    trace_id: "trace_001",
  });
});

test("createErrorPayload matches external error schema", () => {
  const payload = createErrorPayload({
    errorCode: "invalid_request",
    message: "conversationId is required",
    traceId: "trace_002",
  });

  assert.deepEqual(payload, {
    ok: false,
    error: "invalid_request",
    message: "conversationId is required",
    trace_id: "trace_002",
  });
});

test("looksIncompleteMessage detects likely unfinished fragments", () => {
  assert.equal(looksIncompleteMessage("我想问一下"), true);
  assert.equal(looksIncompleteMessage("还有"), true);
  assert.equal(looksIncompleteMessage("黄精怎么吃？"), false);
  assert.equal(looksIncompleteMessage("订单号 123456789"), false);
});

test("buildAgentMessage does not inject raw colleague skill content", () => {
  const message = buildAgentMessage({
    stylePrompt: [
      "---",
      "name: colleague-sudan",
      "description: 苏丹，苏丹食养品牌专属客服",
      "user-invocable: true",
      "---",
      "# 苏丹客服 — Work Skill",
      "## 职责范围",
      "- 私域用户咨询接待，产品介绍与答疑",
    ].join("\n"),
    userMessage: "查一下订单",
    history: [{ role: "user", text: "你好" }],
    knowledgeHits: [],
  });

  assert.equal(
    message.startsWith("当前客服可使用的 skill 为 `metast-mcp`。遇到实时商品、快递、订单查询时优先使用它。"),
    true
  );
  assert.equal(message.includes("name: colleague-sudan"), false);
  assert.equal(message.includes("user-invocable: true"), false);
  assert.equal(message.includes("# 苏丹客服 — Work Skill"), false);
  assert.equal(message.includes("【苏丹人格与回复规则】"), false);
  assert.equal(message.includes("私域用户咨询接待，产品介绍与答疑"), false);
});

test("buildAgentMessage tells the agent to use metast-mcp for product detail questions", () => {
  const message = buildAgentMessage({
    userMessage: "绿壳五黑土鸡蛋168元和88元有什么区别，规格多少枚？",
    history: [],
    knowledgeHits: [],
  });

  assert.equal(message.includes("价格、规格、保质期、区别、库存、是否上架"), true);
  assert.equal(message.includes("先查 `metast-mcp`"), true);
});
