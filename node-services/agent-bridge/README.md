# Sudan Agent Bridge

这个服务负责把第三方 HTTP `POST` 请求桥接到 OpenClaw 的 `main` agent。

## 功能

- `POST /api/agents/chat` 默认调用 `main`
- `POST /api/agents/<agentId>/chat` 显式指定 agent
- 固定 `conversationId` 映射到稳定 `sessionId`
- 支持 `content` 字符串或 `messageList`
- 读取本地 FAQ JSON，命中后把结果作为隐藏上下文注入给 OpenClaw
- Bearer Token 鉴权

## 快速开始

1. 复制环境变量模板：

```bash
cd node-services/agent-bridge
cp .env.example .env
```

2. 修改 `.env`，至少配置：

```env
AGENT_BRIDGE_TOKEN=replace_me
DEFAULT_AGENT_ID=main
OPENCLAW_BIN=openclaw
KNOWLEDGE_FILE=../../knowledge/faq.json
SYSTEM_PROMPT_FILE=../../build/generated/system_prompt.md
```

3. 启动服务：

```bash
node src/server.js
```

## 接口

### 健康检查

```http
GET /health
```

### 默认 main agent

```http
POST /api/agents/chat
Authorization: Bearer <token>
Content-Type: application/json
```

### 显式指定 agent

```http
POST /api/agents/main/chat
Authorization: Bearer <token>
Content-Type: application/json
```

### 最简请求体

```json
{
  "conversationId": "wechat_user_001",
  "content": "你是谁"
}
```

### 带 messageList 的请求体

```json
{
  "conversationId": "wechat_user_001",
  "content": {
    "messageList": [
      { "role": "assistant", "text": "您好，我在这边。" },
      { "role": "user", "text": "黄精适合哪些人群吃？" }
    ]
  }
}
```

### 响应

```json
{
  "agentId": "main",
  "conversationId": "wechat_user_001",
  "sessionId": "bridge:main:wechat_user_001:xxxxxxxxxx",
  "reply": "我是苏丹的数字分身，平时主要帮大家答疑和处理常见咨询。",
  "mediaUrls": [],
  "knowledgeHits": [
    {
      "id": "faq-041",
      "question": "黄精适合哪些人群吃？",
      "score": 12,
      "category": "产品与食养"
    }
  ]
}
```
