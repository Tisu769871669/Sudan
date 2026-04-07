# Sudan Agent Bridge

这个服务负责把第三方 HTTP `POST` 请求桥接到 OpenClaw agent，并对外保持统一协议。

## 接口地址

- `POST /api/agents/chat`
- `POST /api/agents/<agentId>/chat`

## 请求头

```http
Authorization: Bearer <token>
Content-Type: application/json; charset=utf-8
```

## 请求参数

### `conversationId`

- 类型：`string`
- 必填：是
- 说明：会话 ID。同一个用户必须固定同一个值，用来维持连续上下文。

### `conversation_id`

- 类型：`string`
- 必填：否
- 说明：`conversationId` 的兼容别名，二选一即可。
- 建议：新系统统一使用 `conversationId`

### `userId`

- 类型：`string`
- 必填：否
- 说明：用户唯一标识。当前不是必须，仅预留。

### `user_id`

- 类型：`string`
- 必填：否
- 说明：`userId` 的兼容别名。

### `message`

- 类型：`string`
- 必填：否
- 说明：直接传本轮用户消息。

### `content`

- 类型：`string | object`
- 必填：否
- 说明：
  - 如果是 `string`，直接作为本轮用户消息
  - 如果是 `object`，可包含 `messageList`

### `content.messageList`

- 类型：`array`
- 必填：否
- 说明：最近几轮聊天记录。服务会：
  - 取最后一条用户消息作为本轮输入
  - 把最近几轮作为辅助上下文带给 agent

### `content.messageList[].role`

- 类型：`string`
- 必填：否
- 建议值：
  - `user`
  - `assistant`

### `content.messageList[].text`

- 类型：`string`
- 必填：否
- 说明：消息文本

## 当前服务端取值规则

- `conversationId` 或 `conversation_id` 必须至少有一个
- 以下三种任意一种能提取出消息即可：
  - `message`
  - `content` 字符串
  - `content.messageList`

## 推荐最小请求体

```json
{
  "conversationId": "session_001",
  "content": "你好，介绍一下你能做什么"
}
```

## 推荐上下文请求体

```json
{
  "conversationId": "session_001",
  "content": {
    "messageList": [
      { "role": "assistant", "text": "您好，今天想看什么？" },
      { "role": "user", "text": "我想先了解一下会员" },
      { "role": "assistant", "text": "好的呀，您最想了解哪一块呢？" },
      { "role": "user", "text": "会员费是多少？" }
    ]
  }
}
```

## 返回结果字段

### `ok`

- 类型：`boolean`
- 说明：是否成功

### `agent_id`

- 类型：`string`
- 说明：当前调用的 agent，例如：
  - `main`
  - `snowchuang`
  - `yixiang`

### `conversation_id`

- 类型：`string`
- 说明：回显请求里的会话 ID

### `user_id`

- 类型：`string`
- 说明：回显请求里的用户 ID；如果没传，一般是空字符串

### `reply`

- 类型：`string`
- 说明：agent 最终生成的回复文本。调用方最终只需要把这个字段发回微信。

### `session_id`

- 类型：`string`
- 说明：服务内部生成的会话 ID，例如：
  - `bridge_main_session_001`
  - `bridge_snowchuang_session_001`
  - `bridge_yixiang_session_001`

### `trace_id`

- 类型：`string`
- 说明：调试追踪 ID

## 成功返回示例

```json
{
  "ok": true,
  "agent_id": "main",
  "conversation_id": "session_001",
  "user_id": "",
  "reply": "我是苏丹的数字分身，平时主要帮大家答疑和处理常见咨询。您想问产品、订单，还是使用上的问题？",
  "session_id": "bridge_main_session_001",
  "trace_id": "5952a2ee-0ecb-40b6-a21e-b93afd94a8ed"
}
```

## 失败返回示例

```json
{
  "ok": false,
  "error": "invalid_request",
  "message": "conversationId is required",
  "trace_id": "b84d2e69-c6d6-4fd5-a4c9-0d9a7e8d6e6a"
}
```

## 常见错误码

- `unauthorized`
  - 说明：Token 错误或缺失
- `invalid_request`
  - 说明：请求参数不完整
- `agent_execution_failed`
  - 说明：agent 调用失败

## 上下文规则

- 同一个用户必须固定使用同一个 `conversationId`
- `conversationId` 是主上下文键
- `messageList` 只是辅助上下文，不是必须
