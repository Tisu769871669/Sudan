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

Credential loading order:

1. `METAST_MCP_ENV_FILE`, if set
2. `~/.openclaw/workspace/skills/metast-mcp/.env.metast`
3. current working directory `.env.metast`
4. `~/Sudan/.env.metast`
5. `~/.openclaw/.env.metast`

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

## 4. Yugao List

- Method: `GET`
- Path: `/app-api/mcp/api-mcp/yugaoList`

## 5. Member User List

- Method: `GET`
- Path: `/app-api/mcp/api-mcp/memberUserList`
- Query params:
  - `pageNo`: page number
  - `pageSize`: page size

## 6. Member User Order List

- Method: `GET`
- Path: `/app-api/mcp/api-mcp/memberUserOrderList`
- Query params:
  - `pageNo`: page number
  - `pageSize`: page size
  - `userId`: user ID

## 7. Order User Delivery

- Method: `GET`
- Path: `/app-api/mcp/api-mcp/orderUserdelivery`
- Query params:
  - `orderId`: order ID

## 8. IM Group List

- Method: `GET`
- Path: `/system/api/im/groupList`
- Query params:
  - `pageNo`: page number
  - `pageSize`: page size

## 9. Send Single Chat Message

- Method: `GET`
- Path: `/system/api/im/sendChatMesage`
- Query params:
  - `mobile`: recipient mobile number
  - `content`: message content

## 10. Send Group Message

- Method: `GET`
- Path: `/system/api/im/sendGroupMesage`
- Query params:
  - `groupId`: group chat ID
  - `content`: message content
