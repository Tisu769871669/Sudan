---
name: metast-mcp
description: Query and operate Metast MCP customer-service APIs for products, couriers, orders, previews, users, logistics, IM groups, and sending single or group messages. Use when the agent needs live data or customer-service actions from `https://lx.metast.cn` with `mcpKey` and `mcpSecret` headers.
---

# Metast MCP

Use this skill when the agent needs live Metast MCP data for:

- currently listed products
- courier company options
- order lookup by order number
- previews / pre-sale notices
- member user lists and a user's order list
- order logistics by order ID
- IM group lists
- single-user or group message sending

## Quick Start

Ensure credentials are available. The bundled script first loads the first existing file from:

- `METAST_MCP_ENV_FILE`, if set
- the installed skill directory: `~/.openclaw/workspace/skills/metast-mcp/.env.metast`
- the current working directory: `.env.metast`
- `~/Sudan/.env.metast`
- `~/.openclaw/.env.metast`

The env file should define:

- `METAST_MCP_BASE_URL`
- `METAST_MCP_KEY`
- `METAST_MCP_SECRET`

Run one of these:

```bash
python3 scripts/fetch_metast_mcp.py product-list
python3 scripts/fetch_metast_mcp.py product-list --name 商品名
python3 scripts/fetch_metast_mcp.py delivery-express-list
python3 scripts/fetch_metast_mcp.py order-list --no ORDER_NO
python3 scripts/fetch_metast_mcp.py yugao-list
python3 scripts/fetch_metast_mcp.py member-user-list --page-no 1 --page-size 20
python3 scripts/fetch_metast_mcp.py member-user-order-list --page-no 1 --page-size 20 --user-id USER_ID
python3 scripts/fetch_metast_mcp.py order-user-delivery --order-id ORDER_ID
python3 scripts/fetch_metast_mcp.py im-group-list --page-no 1 --page-size 20
python3 scripts/fetch_metast_mcp.py send-chat-message --mobile MOBILE --content "消息内容"
python3 scripts/fetch_metast_mcp.py send-group-message --group-id GROUP_ID --content "消息内容"
```

## Capabilities

### 1. Product List

Use:

```bash
python3 scripts/fetch_metast_mcp.py product-list
python3 scripts/fetch_metast_mcp.py product-list --name 商品名
```

Use when the user asks:

- 现在上架了哪些商品
- 当前有哪些商品在卖
- 帮我查一下商品列表
- 查一下某个商品有没有上架
- 按名称查商品
- 商品价格、规格、净含量、数量、保质期、保存方式
- 两款商品有什么区别，例如“168 元和 88 元有什么区别”
- 鸡蛋、猪肉、山药粉等当前售卖商品的实时详情

### 2. Delivery Express List

Use:

```bash
python3 scripts/fetch_metast_mcp.py delivery-express-list
```

Use when the user asks:

- 有哪些快递公司
- 支持哪些快递
- 查一下快递公司列表

### 3. Order List / Order Lookup

Use:

```bash
python3 scripts/fetch_metast_mcp.py order-list --no ORDER_NO
```

Use when the user provides an order number and wants order information.

### 4. Preview / Yugao List

Use:

```bash
python3 scripts/fetch_metast_mcp.py yugao-list
```

Use when the user asks about current previews, notices, or pre-sale/advance information.

### 5. Member User List

Use:

```bash
python3 scripts/fetch_metast_mcp.py member-user-list --page-no 1 --page-size 20
```

Use when customer service needs paginated member/user information.

### 6. Member User Order List

Use:

```bash
python3 scripts/fetch_metast_mcp.py member-user-order-list --page-no 1 --page-size 20 --user-id USER_ID
```

Use when customer service needs a specific user's paginated order list.

### 7. Order Logistics

Use:

```bash
python3 scripts/fetch_metast_mcp.py order-user-delivery --order-id ORDER_ID
```

Use when customer service needs logistics or delivery details for an order ID.

### 8. IM Group List

Use:

```bash
python3 scripts/fetch_metast_mcp.py im-group-list --page-no 1 --page-size 20
```

Use when customer service needs paginated group chat information.

### 9. Send Single Message

Use:

```bash
python3 scripts/fetch_metast_mcp.py send-chat-message --mobile MOBILE --content "消息内容"
```

Use only after confirming the recipient and content. This endpoint sends a real message to one user.

### 10. Send Group Message

Use:

```bash
python3 scripts/fetch_metast_mcp.py send-group-message --group-id GROUP_ID --content "消息内容"
```

Use only after confirming the group and content. This endpoint sends a real message to a group.

## Workflow

1. Choose the correct endpoint based on the user intent.
2. Send a `GET` request with headers:
   - `mcpKey`
   - `mcpSecret`
3. If the action is `product-list` and the user gave a product name or asked about a product detail, pass the product keyword as query param `name`.
4. If the action is `order-list`, pass the order number as query param `no`.
5. For paginated actions (`member-user-list`, `member-user-order-list`, `im-group-list`), pass `--page-no` and `--page-size`.
6. For user/order/message actions, pass the required IDs or message fields exactly as the script flags describe.
7. Before using `send-chat-message` or `send-group-message`, confirm the recipient and content because the call sends a real message.
8. Parse the JSON response.
9. Summarize the useful fields for the user.
10. If the API returns an error, report the real error and do not fabricate data.

## Output Guidance

- For broad questions, summarize rather than dump raw JSON.
- For exact questions, include the exact returned fields.
- For `product-list`, prefer using `--name` when the user clearly asks about a specific product.
- Treat price, specification, shelf life, storage method, stock, sale status, and product comparisons as `product-list` questions.
- For `order-list`, require an order number before calling.
- For paginated lists, ask for or choose a small page size such as 20 unless the user needs more.
- For message-sending actions, never invent recipients or content; confirm ambiguous details first.
- Keep the response concise unless the user asks for full details.

## Resources

### `scripts/`

- `scripts/fetch_metast_mcp.py`
  Unified CLI for supported Metast MCP and customer-service endpoints.

### `references/`

- `references/api.md`
  Endpoint list, parameters, and environment variable contract.
