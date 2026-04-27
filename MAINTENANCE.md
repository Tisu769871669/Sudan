# 苏丹 OpenClaw 项目维护文档

本文档面向后续维护者，目标是把“苏丹数字分身”这套客服 agent 的结构、生成链路、服务链路、部署链路和高风险点讲清楚。日常只想快速部署时先看 `README.md`；要复刻一套新业务 agent 时看 `AGENT_BUILD_PLAYBOOK.md`；要维护每日自动化任务时看 `docs/AUTOMATION_WORKFLOW.md`；要长期改项目时以本文档为主。

## 1. 项目定位

这个仓库不是单纯的 Web 服务，也不是单纯的 prompt 仓库，而是一套私域客服 agent 交付包：

- `persona/` 维护苏丹客服的人格、风格、规则和话术。
- `distill/` 保存从真实客服聊天记录蒸馏出的风格资产。
- `knowledge/` 保存 FAQ 知识库，供 bridge 注入隐藏上下文。
- `node-services/agent-bridge/` 对外提供 HTTP 接口，把第三方请求转成 OpenClaw CLI 调用。
- `skills/metast-mcp/` 提供实时商品、订单、快递、IM 群等 Metast MCP 查询和操作能力。
- `scripts/` 负责服务器准备、人格部署、skill 安装、systemd 服务和 Nginx HTTPS。
- `deploy/nginx/` 保存线上域名反代模板。
- `mem/`、`.docx` 等文件是蒸馏或运营参考资料，不应当直接暴露给第三方。

核心原则是：`persona` 和 `distill` 负责“怎么说”，`knowledge` 和 `metast-mcp` 负责“说什么不能错”，`agent-bridge` 负责协议、鉴权、上下文、防抖和调用 OpenClaw。

## 2. 目录速览

| 路径 | 作用 | 维护要点 |
| --- | --- | --- |
| `README.md` | 快速说明和部署入口 | 保持命令与实际脚本一致 |
| `AGENT_BUILD_PLAYBOOK.md` | 复刻 agent 的流程手册 | 适合迁移到另一台 OpenClaw 服务器 |
| `docs/API_REFERENCE.md` | Metast MCP API 表格文档 | 接口参数变化时优先同步这里 |
| `docs/AUTOMATION_WORKFLOW.md` | 每日客服自动化流程文档 | cron、dry-run、execute、日志和灰度策略都维护在这里 |
| `build/compose-system-prompt.py` | 拼装最终系统提示词 | 改 `persona/` 后运行它 |
| `build/sync-colleague-distill.py` | 把蒸馏产物同步到 `persona/COLLEAGUE_SKILL_V2.md` | 改 `distill/colleague-skill-generated/sudan_service` 后运行它 |
| `build/generated/system_prompt.md` | 生成后的最终 prompt | 生成物，不建议手改 |
| `persona/` | prompt 源文件 | 当前 compose 脚本读取 `IDENTITY.md`、`DISTILLED_SERVICE.md`、`COLLEAGUE_SKILL_V2.md`、`STYLE.md`、`RULES.md`、`OPENING.md` |
| `knowledge/faq.json` | bridge 实际检索的结构化 FAQ | 必须是 JSON 数组 |
| `knowledge/faq.md` | 人看的 FAQ 文档 | 与 `faq.json` 同步维护 |
| `node-services/agent-bridge/` | HTTP Bridge 服务 | 纯 Node 内置模块，Node >= 20 |
| `skills/metast-mcp/` | 实时业务 API skill | 线上优先使用这个统一 skill |
| `scripts/sudan_daily_automation.py` | 每日客服自动化脚本 | 默认 dry-run，真实发送必须加 `--execute` |
| `.env.metast` | Metast MCP 凭证 | 已在 `.gitignore`，不要提交或粘贴真实值 |
| `node-services/agent-bridge/.env` | bridge 运行配置 | 已在 `.gitignore`，不要提交 token |
| `mem/wx_pad_private_message.xlsx` | 原始聊天样本 | 含私域聊天数据，谨慎传播 |
| `AI客服每日工作流程.docx` | 每日客服运营 SOP | 用来理解业务，不是服务运行依赖 |

特别注意：`persona/SOUL.md` 当前看起来像完整系统提示词副本，但 `build/compose-system-prompt.py` 并不读取它。部署时真正复制到 OpenClaw workspace 的 `SOUL.md` 来自 `build/generated/system_prompt.md`。以后改人格源时，不要把 `persona/SOUL.md` 当唯一源头。

## 3. Prompt 生成链路

推荐维护顺序：

```bash
python build/sync-colleague-distill.py
python build/compose-system-prompt.py
```

`sync-colleague-distill.py` 从 `distill/colleague-skill-generated/sudan_service/persona.md` 和 `work.md` 合并生成 `persona/COLLEAGUE_SKILL_V2.md`。

`compose-system-prompt.py` 按固定顺序拼接：

1. `persona/IDENTITY.md`
2. `persona/DISTILLED_SERVICE.md`
3. `persona/COLLEAGUE_SKILL_V2.md`
4. `persona/STYLE.md`
5. `persona/RULES.md`
6. `persona/OPENING.md`

输出到 `build/generated/system_prompt.md`。

维护判断：

- 改身份、服务范围、边界：优先改 `persona/IDENTITY.md`。
- 改真实客服风格沉淀：优先改 `persona/DISTILLED_SERVICE.md` 或蒸馏源，再同步。
- 改实时商品/订单必须查 skill 的规则：改 `persona/RULES.md` 和必要的 bridge prompt。
- 改开场话术：改 `persona/OPENING.md`。
- 不要直接改 `build/generated/system_prompt.md`，否则下次生成会被覆盖。

## 4. Bridge 服务架构

服务入口是 `node-services/agent-bridge/src/server.js`，使用 Node 原生 `http`，没有 Express 和第三方依赖。`package.json` 只有两个脚本：

```bash
npm test
npm start
```

请求链路：

1. `GET /health` 返回服务健康、默认 agent、知识库路径、OpenClaw 路径。
2. `POST /api/agents/chat` 使用 `DEFAULT_AGENT_ID`，默认是 `main`。
3. `POST /api/agents/<agentId>/chat` 显式指定 agent。
4. 校验 `Authorization: Bearer <AGENT_BRIDGE_TOKEN>`，如果 token 为空则跳过鉴权。
5. `extractConversation()` 提取 `conversationId`、`userId`、历史消息和本轮用户消息。
6. 按 `agentId + conversationId` 建队列，短时间消息先防抖合并。
7. 同一会话上一轮还没跑完时，后续消息排队，不会丢。
8. 合并后的用户消息进入 `knowledgeStore.search()` 做 FAQ 检索。
9. `buildAgentMessage()` 拼隐藏上下文，要求 agent 短答，并提醒实时商品、快递、订单要优先用 `metast-mcp`。
10. `runOpenClawAgent()` 调用 `openclaw agent --agent ... --session-id ... --message ...`。
11. 返回统一 JSON。

请求体支持三种输入方式，至少要能提取出一条用户消息：

```json
{
  "conversationId": "session_001",
  "content": "你好，介绍一下你能做什么"
}
```

```json
{
  "conversationId": "session_001",
  "message": "会员费是多少？"
}
```

```json
{
  "conversationId": "session_001",
  "content": {
    "messageList": [
      { "role": "assistant", "text": "您好，有什么可以帮助？" },
      { "role": "user", "text": "黄精适合哪些人吃？" }
    ]
  }
}
```

成功响应结构：

```json
{
  "ok": true,
  "agent_id": "main",
  "conversation_id": "session_001",
  "user_id": "",
  "reply": "回复文本",
  "session_id": "bridge_main_session_001",
  "trace_id": "..."
}
```

防抖行为要和调用方讲清楚：同一批合并消息里，只有最后一个请求会拿到真实 `reply`，前面的请求会返回 `reply: ""`。调用方只应把非空 `reply` 发回微信或用户端。

## 5. Bridge 环境变量

配置模板在 `node-services/agent-bridge/.env.example`。真实 `.env` 不要提交。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PORT` | `9070` | HTTP 服务端口 |
| `AGENT_BRIDGE_TOKEN` | 空 | Bearer token；为空时不鉴权 |
| `OPENCLAW_BIN` | `openclaw` | OpenClaw CLI 路径或命令名 |
| `DEFAULT_AGENT_ID` | `main` | `/api/agents/chat` 默认调用的 agent |
| `AGENT_TIMEOUT_SECONDS` | `120` | OpenClaw agent 超时时间 |
| `OPENCLAW_FORCE_LOCAL` | `0` | 为 `1` 时追加 `--local` |
| `KNOWLEDGE_FILE` | `../../knowledge/faq.json` | FAQ JSON 路径 |
| `SYSTEM_PROMPT_FILE` | `../../build/generated/system_prompt.md` | 健康检查展示用，目前不再完整注入 |
| `COLLEAGUE_SKILL_FILE` | 空或 workspace skill 路径 | 健康检查展示用，当前 bridge 不再注入完整 skill |
| `KB_TOP_K` | `3` | 每轮最多注入几条 FAQ |
| `KB_MIN_SCORE` | `3` | FAQ 命中最低分 |
| `MAX_HISTORY_MESSAGES` | `8` | 最多带入几条历史消息 |
| `DEBOUNCE_WINDOW_MS` | `2500` | 基础防抖窗口 |
| `INCOMPLETE_MESSAGE_EXTRA_WAIT_MS` | `2500` | 疑似未说完整时额外等待 |
| `MAX_DEBOUNCE_WINDOW_MS` | `6000` | 最大防抖窗口 |
| `LOG_LEVEL` | `info` | `error` / `warn` / `info` / `debug` |

`.env.example` 已包含新的防抖变量；如果线上旧 `.env` 没写，代码会使用默认值。

## 6. FAQ 知识库维护

当前 `knowledge/faq.json` 有 52 条，字段结构为：

```json
{
  "id": "faq-001",
  "category": "账号与小程序",
  "question": "如何创建账号？",
  "answer": "您用手机号在小程序上登录即可生成属于您的账号！",
  "keywords": ["账号", "登录", "小程序"]
}
```

分类包括：

- 账号与小程序
- 商城与直播
- 订单与支付
- 产品与食养
- 双极水使用
- 客服与社群

检索逻辑在 `src/knowledge.js`：

- 先做中英文大小写、标点、空白归一化。
- 问题包含、关键词包含会加高分。
- 再用中文 bigram 与 question / answer 做重叠计分。
- 低于 `KB_MIN_SCORE` 的条目不会注入。

维护建议：

- 改 FAQ 时同时维护 `faq.md` 和 `faq.json`。
- `keywords` 要写用户会说的口语关键词，不只写正式品名。
- 产品价格、库存、规格、是否上架等实时信息不要写死在 FAQ；应走 `metast-mcp`。
- 食养、功效、适用人群类内容要避免强医疗承诺，写成日常养护建议。
- 改完后至少跑 `npm test`，再用一个明确问题手测命中效果。

## 7. Metast MCP skill

线上应优先安装和使用 `skills/metast-mcp/`，它已经合并了早期 `metast-product-list` 和 `metast-delivery-express-list` 的能力。安装脚本：

```bash
bash scripts/install-metast-mcp-skills.sh
```

这个脚本会覆盖目标 workspace 下已有的 `metast-mcp`、`metast-product-list`、`metast-delivery-express-list` 目录。执行前确认目标目录是本业务 agent 的 workspace。

凭证加载顺序：

1. `METAST_MCP_ENV_FILE`
2. 已安装 skill 目录下的 `.env.metast`
3. 当前工作目录 `.env.metast`
4. `~/Sudan/.env.metast`
5. `~/.openclaw/.env.metast`

`.env.metast` 需要配置：

```env
METAST_MCP_BASE_URL=https://lx.metast.cn
METAST_MCP_KEY=<your key>
METAST_MCP_SECRET=<your secret>
```

常用命令：

```bash
python3 ~/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py product-list --name 商品名
python3 ~/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py delivery-express-list
python3 ~/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py order-list --no ORDER_NO
python3 ~/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py member-user-list --page-no 1 --page-size 20
python3 ~/.openclaw/workspace/skills/metast-mcp/scripts/fetch_metast_mcp.py im-group-list --page-no 1 --page-size 20
```

高风险能力：

- `send-chat-message` 会真实给用户发消息。
- `send-group-message` 会真实发群消息。
- 这两个能力必须先确认收件人、群 ID 和内容，不能让 agent 自行猜。

已知接口细节：

- IM 接口路径使用 `/prod-api/system/api/im/...`。
- 后端接口名里 `sendChatMesage`、`sendGroupMesage` 拼写就是这样，除非后端改接口，否则不要自行改成 `Message`。
- `api接口.txt` 记录过 `productList` 后端表现为必须传非空 `name`；如果要支持“列出所有商品”，先用真实接口验证当前后端是否已经放开。

## 8. 部署和服务

### 服务器准备

```bash
bash scripts/prepare-server.sh
```

它会检查 `git`、`python3`、`openclaw`，创建 `.venv`，并安装 `PyYAML`，供部署脚本解析 OpenClaw YAML 配置。

### 部署人格和知识库

```bash
bash scripts/apply-openclaw-persona.sh
```

脚本会：

1. 运行 `sync-colleague-distill.py`。
2. 运行 `compose-system-prompt.py`。
3. 探测 OpenClaw 配置路径和 `main` workspace。
4. 视配置结构决定是否直接写 `system_prompt`。
5. 把 `IDENTITY.md`、`STYLE.md`、`RULES.md`、`OPENING.md`、生成后的 `SOUL.md`、FAQ 复制到 OpenClaw workspace。
6. 写入 workspace 级 `AGENTS.md`。
7. 尝试同步 OpenClaw identity。
8. 重启 OpenClaw gateway。
9. 如果内置 gateway service disabled，则尝试安装 systemd 兜底服务。

注意：这个脚本负责人格和 FAQ，不负责安装 `metast-mcp` skill。实时查询能力要另外执行 `scripts/install-metast-mcp-skills.sh`。

### 安装 Bridge systemd 服务

```bash
bash scripts/install-agent-bridge-service.sh
```

它会生成 `/etc/systemd/system/openclaw-agent-bridge.service`，读取 `node-services/agent-bridge/.env`，并用当前用户启动 Node 服务。

### 安装 Nginx HTTPS

```bash
bash scripts/install-nginx-https.sh
```

默认：

- 域名：`sdseoul.metast.cn`
- 反代目标：`127.0.0.1:9070`
- 配置模板：`deploy/nginx/sdseoul.metast.cn.conf`
- 证书目录：`/etc/nginx/ssl/`

证书更新：

```bash
bash scripts/update-vxssl.sh
```

它会下载远端证书和私钥，比较 MD5，有变化才替换并 reload nginx。

## 9. 本地验证

Bridge 单测：

```bash
cd node-services/agent-bridge
npm test
```

当前单测覆盖：

- FAQ 文本归一化与评分
- 请求协议兼容字段
- `session_id` 格式
- 成功/失败响应 schema
- 疑似未说完整消息判断
- bridge prompt 不再注入完整 colleague skill
- 商品详情问题提示优先使用 `metast-mcp`

生成 prompt：

```bash
python build/compose-system-prompt.py
```

健康检查：

```bash
curl -sS http://127.0.0.1:9070/health
```

聊天测试：

```bash
curl -sS -X POST http://127.0.0.1:9070/api/agents/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data-binary '{
    "conversationId": "test_001",
    "content": "黄精适合哪些人群吃？"
  }'
```

上线前建议至少测这些问题：

- `你好`：应只回复 `您好，有什么可以帮助？`
- `你是谁`：应介绍“苏丹的数字分身”。
- `黄精适合哪些人吃`：应短答并避免医疗承诺。
- `鸡蛋 168 和 88 有什么区别`：应触发优先查 `metast-mcp` 的行为。
- `订单号 123456789 帮我查一下`：应走订单查询路径。
- `我进不去直播间了`：应先安抚，再说联系/排查动作。

## 10. 常见维护场景

### 修改人格或话术

1. 找到对应 `persona/*.md` 源文件。
2. 保持“短句、真人感、先接住再给动作”的风格。
3. 避免强医疗、强疗效、强承诺。
4. 运行 `python build/compose-system-prompt.py`。
5. 跑 `npm test`。
6. 部署时运行 `bash scripts/apply-openclaw-persona.sh`。

### 更新蒸馏资产

1. 更新 `distill/colleague-skill-generated/sudan_service/persona.md` 或 `work.md`。
2. 运行 `python build/sync-colleague-distill.py`。
3. 检查 `persona/COLLEAGUE_SKILL_V2.md` 是否只体现可上线的风格，不直接复刻高风险聊天。
4. 运行 `python build/compose-system-prompt.py`。

### 更新 FAQ

1. 从 `knowledge/faq-source.txt` 或业务资料整理内容。
2. 同步更新 `knowledge/faq.md` 和 `knowledge/faq.json`。
3. 确认 JSON 是数组，字段包含 `id`、`category`、`question`、`answer`、`keywords`。
4. 把实时信息从 FAQ 中剥离，交给 `metast-mcp`。
5. 跑 `npm test`，再用 curl 或线上 bridge 验证。

### 修改 HTTP 协议

1. 优先改 `extractConversation()` 和相关单测。
2. 确认兼容旧字段：`conversationId` / `conversation_id`，`userId` / `user_id`。
3. 不要轻易改变响应字段名，外部调用方依赖 `reply`、`ok`、`trace_id`。
4. 防抖合并会影响多请求返回，改之前先和调用方确认。

### 修改 Metast MCP 接口

1. 先改 `skills/metast-mcp/references/api.md`。
2. 再改 `scripts/fetch_metast_mcp.py` 的 `ENDPOINTS` 和参数构造。
3. 更新 `SKILL.md` 的触发场景和示例。
4. 对真实发送消息类接口保留人工确认要求。
5. 安装到目标 workspace 后用小 page size 或明确测试数据验证。

## 11. 排障手册

| 现象 | 优先检查 |
| --- | --- |
| `/health` 访问失败 | Bridge 服务是否启动、端口是否被占用、systemd 日志 |
| `401 unauthorized` | `AGENT_BRIDGE_TOKEN` 和请求头是否一致 |
| `400 conversationId is required` | 请求体是否传了 `conversationId` 或兼容字段 |
| `400 message or content is required` | 请求体是否能提取出用户消息 |
| 前几个请求 `reply` 为空 | 同一会话防抖合并的预期行为，只处理最后一个非空回复 |
| `502 openclaw agent failed` | OpenClaw CLI、agent id、模型 provider、gateway、本机 `openclaw agent` 是否可用 |
| FAQ 明明有但没命中 | `KB_MIN_SCORE` 是否过高、关键词是否不贴近用户说法 |
| 商品/订单没有查实时接口 | OpenClaw workspace 是否安装了 `metast-mcp`，prompt 是否仍要求优先查 skill |
| Nginx 502 | Bridge 是否监听 9070，Nginx 反代端口是否一致 |
| 证书异常 | `update-vxssl.sh`、证书文件权限、`nginx -t` |

常用日志：

```bash
journalctl -u openclaw-agent-bridge.service -n 100 --no-pager
journalctl -u openclaw-gateway.service -n 100 --no-pager
systemctl status openclaw-agent-bridge.service --no-pager
systemctl status nginx --no-pager
```

## 12. 安全和合规注意事项

- `.env.metast`、`node-services/agent-bridge/.env` 都包含敏感凭证，已被 `.gitignore` 忽略，不要提交。
- 如果凭证曾经被复制到聊天、文档、截图或公开仓库，应立即轮换。
- `mem/wx_pad_private_message.xlsx` 是原始私域聊天数据，包含用户消息，不能随意外发。
- `AI客服每日工作流程.docx` 属于运营 SOP，包含群发、私发和活动动作，公开前要确认业务方同意。
- 产品、食养、双极水相关内容容易接近医疗宣传边界，agent 应使用“日常养护、使用建议、进一步确认”的表达，不做诊断、疗效保证或替代医生判断。
- `send-chat-message`、`send-group-message` 是真实发送动作，必须有人确认对象和内容。

## 13. 发布前检查清单

- `git status` 确认没有误提交 `.env`、`.env.metast`、私密聊天数据或临时文件。
- `npm test` 通过。
- `python build/compose-system-prompt.py` 能生成 `build/generated/system_prompt.md`。
- `knowledge/faq.json` 能被 JSON 解析，且不是空数组。
- OpenClaw 本机 `openclaw agent --agent main --message "你好"` 可用。
- `metast-mcp` 已安装到目标 agent workspace。
- `/health` 正常。
- 鉴权请求正常，错误 token 返回 401。
- Nginx `nginx -t` 通过。
- 至少用“打招呼、身份、FAQ、实时商品、订单、售后情绪”六类问题抽测。

## 14. 当前已知技术债与已缓解项

- `README.md` 仍描述 `persona/SOUL.md` 是源文件之一，但 compose 脚本实际不读取它；维护时以脚本为准。
- `persona/SOUL.md` 当前有未提交的换行差异，且更像生成稿副本，后续可考虑明确改名或移除出源链路。
- `skills/metast-product-list/` 和 `skills/metast-delivery-express-list/` 是早期拆分 skill，线上应收敛到 `metast-mcp`。
- `api接口.txt` 与 `metast-mcp` 的 product-list 示例存在一点差异：接口记录里提到后端可能要求非空 `name`，而 skill 示例允许不传；要以后端实测为准。
- 已缓解：线上通过 `openclaw-agent-pool-bridge` 接管 `9070` 入口，`main` 逻辑 agent 配置 5 个 worker。苏丹原 workspace 已同步为 worker 模板，并下发到所有 worker workspace。该方案缓解了单一 `main` agent 承压和多会话并发隔离问题；后续仍需监控队列深度、`429 queue_timeout`、单机资源占用和 OpenClaw 子进程启动开销。
- FAQ、`faq-source.txt`、`问题.txt` 存在内容重复，后续最好明确唯一源，再生成人读版和 JSON 版，减少漂移。
