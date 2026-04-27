# Metast MCP 接口参考

## 基础信息

- Base URL：`https://lx.metast.cn`
- 请求方式：`GET`
- 通用请求头：
  - `mcpKey`
  - `mcpSecret`
  - `Accept: application/json`

脚本需要的环境变量：

- `METAST_MCP_BASE_URL`
- `METAST_MCP_KEY`
- `METAST_MCP_SECRET`

凭证加载顺序：

1. `METAST_MCP_ENV_FILE`
2. `~/.openclaw/workspace/skills/metast-mcp/.env.metast`
3. 当前工作目录 `.env.metast`
4. `~/Sudan/.env.metast`
5. `~/.openclaw/.env.metast`

## 1. 商品列表/商品搜索

- Method：`GET`
- Path：`/app-api/mcp/api-mcp/productList`
- Query 参数：
  - `name`：商品名称关键词。实测建议传非空值。

## 2. 快递公司列表

- Method：`GET`
- Path：`/app-api/mcp/api-mcp/deliveryExpressList`
- Query 参数：无

## 3. 订单号查询

- Method：`GET`
- Path：`/app-api/mcp/api-mcp/orderList`
- Query 参数：
  - `no`：订单号

## 4. 直播/预告列表

- Method：`GET`
- Path：`/app-api/mcp/api-mcp/yugaoList`
- Query 参数：无

## 5. 会员列表

- Method：`GET`
- Path：`/app-api/mcp/api-mcp/memberUserList`
- Query 参数：
  - `pageNo`：页码
  - `pageSize`：每页数量

## 6. 会员订单分页

- Method：`GET`
- Path：`/app-api/mcp/api-mcp/memberUserOrderList`
- Query 参数：
  - `pageNo`：页码
  - `pageSize`：每页数量
  - `mobile`：会员手机号，必填
  - `status`：订单状态，必填
  - `userId`：会员用户 ID，可选

## 7. 订单物流详情

- Method：`GET`
- Path：`/app-api/mcp/api-mcp/orderUserdelivery`
- Query 参数：
  - `orderId`：订单 ID

## 8. IM 群列表

- Method：`GET`
- Path：`/prod-api/system/api/im/groupList`
- Query 参数：
  - `pageNo`：页码
  - `pageSize`：每页数量
- 关键字段：
  - `id`：数字 ID，发送群消息时使用。
  - `gid`：微信 chatroom 标识，只用于排查，不能传给发送接口。

## 9. 发送单人消息

- Method：`GET`
- Path：`/prod-api/system/api/im/sendChatMesage`
- Query 参数：
  - `mobile`：接收人手机号
  - `content`：消息内容
- 风险：会真实发送消息，调用前必须确认手机号和内容。

## 10. 发送群消息

- Method：`GET`
- Path：`/prod-api/system/api/im/sendGroupMesage`
- Query 参数：
  - `groupId`：`/prod-api/system/api/im/groupList` 返回的数字 `id`，不能使用 `gid`
  - `content`：消息内容
- 风险：会真实发送群消息，调用前必须确认群和内容。
