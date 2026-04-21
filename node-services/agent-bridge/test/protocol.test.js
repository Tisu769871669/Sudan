const test = require("node:test");
const assert = require("node:assert/strict");
const {
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
