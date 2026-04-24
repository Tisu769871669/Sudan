---
name: metast-mcp
description: Query the Metast MCP APIs for listed products, courier companies, and order details. Use when the agent needs live data from `https://lx.metast.cn/app-api/mcp/api-mcp/productList`, `deliveryExpressList`, or `orderList` with `mcpKey` and `mcpSecret` headers.
---

# Metast MCP

Use this skill when the agent needs live Metast MCP data for:

- currently listed products
- courier company options
- order lookup by order number

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

## Workflow

1. Choose the correct endpoint based on the user intent.
2. Send a `GET` request with headers:
   - `mcpKey`
   - `mcpSecret`
3. If the action is `product-list` and the user gave a product name, pass it as query param `name`.
4. If the action is `order-list`, pass the order number as query param `no`.
5. Parse the JSON response.
6. Summarize the useful fields for the user.
7. If the API returns an error, report the real error and do not fabricate data.

## Output Guidance

- For broad questions, summarize rather than dump raw JSON.
- For exact questions, include the exact returned fields.
- For `product-list`, prefer using `--name` when the user clearly asks about a specific product.
- For `order-list`, require an order number before calling.
- Keep the response concise unless the user asks for full details.

## Resources

### `scripts/`

- `scripts/fetch_metast_mcp.py`
  Unified CLI for all three Metast MCP endpoints.

### `references/`

- `references/api.md`
  Endpoint list, parameters, and environment variable contract.
