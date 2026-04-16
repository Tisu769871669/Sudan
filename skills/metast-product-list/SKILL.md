---
name: metast-product-list
description: Fetch the currently listed products from the Metast MCP API. Use when the agent needs the live catalog of currently listed goods from `https://lx.metast.cn/app-api/mcp/api-mcp/productList` with `mcpKey` and `mcpSecret` headers.
---

# Metast Product List

Use this skill when the agent needs the latest list of currently listed products from the Metast MCP API.

## Quick Start

Ensure these environment variables are set:

- `METAST_MCP_BASE_URL`
- `METAST_MCP_KEY`
- `METAST_MCP_SECRET`

Run:

```bash
python scripts/fetch_product_list.py
```

## Workflow

1. Call the API with a `GET` request.
2. Pass `mcpKey` and `mcpSecret` in the request headers.
3. Parse the JSON response.
4. Extract useful fields such as:
   - product name
   - sku or id
   - price
   - status
   - stock
   - labels or category
5. If the response is large, summarize it for the user instead of dumping the raw JSON unless the user explicitly wants the raw payload.

## Output Guidance

- When the user asks broadly, summarize the available products in plain language.
- When the user asks for exact data, provide the specific returned fields.
- If the API fails, report the HTTP error or transport error directly and do not fabricate product data.

## Resources

### `scripts/`

- `scripts/fetch_product_list.py`
  Perform the authenticated `GET` call and print formatted JSON.

### `references/`

- `references/api.md`
  Endpoint contract and required environment variables.
