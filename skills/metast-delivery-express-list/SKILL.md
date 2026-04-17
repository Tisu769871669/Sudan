---
name: metast-delivery-express-list
description: Fetch the courier company list from the Metast MCP API. Use when the agent needs the live delivery express options from `https://lx.metast.cn/app-api/mcp/api-mcp/deliveryExpressList` with `mcpKey` and `mcpSecret` headers.
---

# Metast Delivery Express List

Use this skill when the agent needs the latest courier company list from the Metast MCP API.

## Quick Start

Ensure these environment variables are set:

- `METAST_MCP_BASE_URL`
- `METAST_MCP_KEY`
- `METAST_MCP_SECRET`

Run:

```bash
python3 scripts/fetch_delivery_express_list.py
```

## Workflow

1. Call the API with a `GET` request.
2. Pass `mcpKey` and `mcpSecret` in the request headers.
3. Parse the JSON response.
4. Extract useful fields such as:
   - express company name
   - express company code
   - enabled or default status
5. Summarize the available companies unless the user explicitly asks for raw data.

## Output Guidance

- When the user asks "which express companies are available", return a concise list.
- When the user asks for exact codes or defaults, include those returned fields.
- If the API fails, return the real error and do not fabricate courier data.

## Resources

### `scripts/`

- `scripts/fetch_delivery_express_list.py`
  Perform the authenticated `GET` call and print formatted JSON.

### `references/`

- `references/api.md`
  Endpoint contract and required environment variables.
