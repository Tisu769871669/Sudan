---
name: metast-mcp
description: 查询和操作 Metast MCP 客服接口，包括商品、快递、订单、直播预告、会员、物流、IM 群列表，以及单人/群消息发送。适用于需要 `https://lx.metast.cn` 实时数据或客服动作的场景，请使用 `mcpKey` 和 `mcpSecret` 请求头。
---

# Metast MCP 客服接口能力

当 agent 需要实时业务数据或客服操作时使用本 skill。典型场景包括：

- 查询当前上架商品、价格、规格、库存和商品对比。
- 查询快递公司列表。
- 按订单号查询订单。
- 查询直播预告、预售或活动提醒。
- 查询会员列表和会员订单列表。
- 按订单 ID 查询物流。
- 查询 IM 群列表。
- 给单个用户或群发送消息。

注意：`send-chat-message` 和 `send-group-message` 会真实触达用户或群，必须先确认收件人、群、内容和执行意图。

## 快速开始

先确认凭证可用。脚本会按顺序读取第一个存在的凭证文件：

1. `METAST_MCP_ENV_FILE`
2. 已安装 skill 目录：`~/.openclaw/workspace/skills/metast-mcp/.env.metast`
3. 当前工作目录：`.env.metast`
4. `~/Sudan/.env.metast`
5. `~/.openclaw/.env.metast`

`.env.metast` 需要包含：

```env
METAST_MCP_BASE_URL=https://lx.metast.cn
METAST_MCP_KEY=你的 key
METAST_MCP_SECRET=你的 secret
```

常用命令：

```bash
python3 scripts/fetch_metast_mcp.py product-list --name 商品名
python3 scripts/fetch_metast_mcp.py delivery-express-list
python3 scripts/fetch_metast_mcp.py order-list --no ORDER_NO
python3 scripts/fetch_metast_mcp.py yugao-list
python3 scripts/fetch_metast_mcp.py member-user-list --page-no 1 --page-size 20
python3 scripts/fetch_metast_mcp.py member-user-order-list --page-no 1 --page-size 20 --mobile MOBILE --status STATUS
python3 scripts/fetch_metast_mcp.py order-user-delivery --order-id ORDER_ID
python3 scripts/fetch_metast_mcp.py im-group-list --page-no 1 --page-size 20
python3 scripts/fetch_metast_mcp.py send-chat-message --mobile MOBILE --content "消息内容"
python3 scripts/fetch_metast_mcp.py send-group-message --group-id GROUP_ID --content "消息内容"
```

## 能力说明

### 1. 商品列表/商品搜索

```bash
python3 scripts/fetch_metast_mcp.py product-list --name 商品名
```

适用问题：

- 现在有哪些商品在卖？
- 某个商品有没有上架？
- 商品价格、规格、净含量、数量、保质期、保存方式是什么？
- 两款商品有什么区别，例如“168 元和 88 元有什么区别”？
- 鸡蛋、猪肉、山药粉等当前售卖商品的实时详情。

维护提醒：实测后端更适合传非空 `name`。如果用户问具体商品，优先把关键词传给 `--name`。

### 2. 快递公司列表

```bash
python3 scripts/fetch_metast_mcp.py delivery-express-list
```

适用问题：

- 支持哪些快递？
- 有哪些快递公司？
- 快递公司编码是什么？

### 3. 订单号查询

```bash
python3 scripts/fetch_metast_mcp.py order-list --no ORDER_NO
```

适用场景：用户主动提供订单号，并要求查询订单情况。

没有订单号时不要编造，也不要猜订单。应先请用户补充订单号或手机号等业务允许的信息。

### 4. 直播/预告列表

```bash
python3 scripts/fetch_metast_mcp.py yugao-list
```

适用问题：

- 今天有没有直播？
- 直播什么时候开始？
- 当前有哪些预告或预售信息？

### 5. 会员列表

```bash
python3 scripts/fetch_metast_mcp.py member-user-list --page-no 1 --page-size 20
```

适用场景：客服需要分页查看会员信息，或自动化脚本需要获取私发目标。

### 6. 会员订单分页

```bash
python3 scripts/fetch_metast_mcp.py member-user-order-list --page-no 1 --page-size 20 --mobile MOBILE --status STATUS
```

适用场景：按会员手机号和订单状态主动扫描订单，用于物流通知、签收提醒、评价提醒等自动化流程。

维护提醒：

- 实测需要 `mobile` 和 `status`。
- `userId` 是可选参数。
- 订单状态枚举含义需要以业务确认结果为准。

### 7. 订单物流详情

```bash
python3 scripts/fetch_metast_mcp.py order-user-delivery --order-id ORDER_ID
```

适用场景：已经拿到订单 ID，需要查询物流详情。

### 8. IM 群列表

```bash
python3 scripts/fetch_metast_mcp.py im-group-list --page-no 1 --page-size 20
```

适用场景：查找可发送的群目标。

重要字段：

- `id`：发送群消息时使用的数字 ID。
- `gid`：微信 chatroom 标识，例如 `53220657641@chatroom`，只用于排查，不能传给发送接口。

### 9. 发送单人消息

```bash
python3 scripts/fetch_metast_mcp.py send-chat-message --mobile MOBILE --content "消息内容"
```

这个接口会真实给用户发消息。只有在手机号和内容都明确时才能调用。

### 10. 发送群消息

```bash
python3 scripts/fetch_metast_mcp.py send-group-message --group-id GROUP_ID --content "消息内容"
```

这个接口会真实发群消息。`GROUP_ID` 必须使用 `im-group-list` 返回的数字 `id`，不能使用 `gid` 或会员分组 `groupId`。

## 操作流程

1. 根据用户意图选择正确 action。
2. 使用 `GET` 请求，并带上 `mcpKey`、`mcpSecret`。
3. 商品问题优先使用 `product-list --name 关键词`。
4. 订单号查询必须传 `order-list --no 订单号`。
5. 分页接口统一传 `--page-no` 和 `--page-size`。
6. 会员订单扫描必须传 `--mobile` 和 `--status`。
7. 真实发送消息前，必须确认目标和内容。
8. 解析 JSON 返回，提取对用户有用的信息。
9. API 报错时，返回真实错误，不要编造数据。

## 回复建议

- 用户问泛问题时，做简洁归纳，不要直接倾倒完整 JSON。
- 用户问精确字段时，可以引用接口返回的具体字段。
- 商品价格、规格、库存、上下架状态、商品对比都应走 `product-list`。
- 订单查询必须有订单号；主动订单扫描走 `member-user-order-list`。
- 发消息类 action 不要替用户猜目标或内容。
- 语气保持客服口吻，短句、清楚、少承诺。

## 相关资源

### `scripts/`

- `scripts/fetch_metast_mcp.py`：统一 CLI，封装当前支持的 Metast MCP 和客服接口。
- `scripts/fetch_metast_mcp_test.py`：CLI 参数和 URL 构造的单元测试。

### `references/`

- `references/api.md`：接口路径、参数和凭证约定。

### 项目文档

- `docs/API_REFERENCE.md`：面向维护者的 API 表格。
- `docs/AUTOMATION_WORKFLOW.md`：每日自动化任务、测试和 cron 配置。
