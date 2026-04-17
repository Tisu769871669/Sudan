# Metast MCP APIs

Base URL:

- `https://lx.metast.cn`

Headers required for all requests:

- `mcpKey`
- `mcpSecret`

Environment variables expected by the bundled script:

- `METAST_MCP_BASE_URL`
- `METAST_MCP_KEY`
- `METAST_MCP_SECRET`

## 1. Product List

- Method: `GET`
- Path: `/app-api/mcp/api-mcp/productList`
- Query params:
  - `name`: optional product name filter

## 2. Delivery Express List

- Method: `GET`
- Path: `/app-api/mcp/api-mcp/deliveryExpressList`

## 3. Order List

- Method: `GET`
- Path: `/app-api/mcp/api-mcp/orderList`
- Query params:
  - `no`: order number
