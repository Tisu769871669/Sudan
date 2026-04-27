# 苏丹客服自动化 API 文档

本文档用于维护苏丹客服自动化流程所需的 API 能力。所有 Metast MCP 接口默认 Base URL 为 `https://lx.metast.cn`，请求头需要 `mcpKey`、`mcpSecret`、`Accept: application/json`。

相关流程、测试命令和 cron 配置请看 `docs/AUTOMATION_WORKFLOW.md`。

## Metast MCP 接口

| 能力 | Action | Method | Path | 必填参数 | 可选参数 | 自动化用途 | 注意事项 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 商品列表/商品搜索 | `product-list` | `GET` | `/app-api/mcp/api-mcp/productList` | `name` | 无 | 每日蔬菜推送、商品详情查询、商品对比 | 实测后端更适合传非空 `name`；蔬菜推送可用 `name=蔬菜` 或 `name=菜` |
| 快递公司列表 | `delivery-express-list` | `GET` | `/app-api/mcp/api-mcp/deliveryExpressList` | 无 | 无 | 客服回答支持哪些快递 | 当前自动化流程暂不需要群发 |
| 订单号查询 | `order-list` | `GET` | `/app-api/mcp/api-mcp/orderList` | `no` | 无 | 用户提供订单号时查询订单 | 适合被动客服问答，不适合全量主动扫描 |
| 直播/预告列表 | `yugao-list` | `GET` | `/app-api/mcp/api-mcp/yugaoList` | 无 | 无 | 直播提醒、直播标题和开播时间获取 | 返回字段含 `title`、`name`、`openTime`、`status`；若要直播链接/福利亮点，需看返回内容是否足够 |
| 会员列表 | `member-user-list` | `GET` | `/app-api/mcp/api-mcp/memberUserList` | `pageNo`、`pageSize` | 无 | 私发早安问候、活动通知、订单轮询对象来源 | 返回手机号 `mobile`、姓名/昵称、会员分组、用户 ID 等 |
| 用户订单分页 | `member-user-order-list` | `GET` | `/app-api/mcp/api-mcp/memberUserOrderList` | `pageNo`、`pageSize`、`mobile`、`status` | `userId` | 主动轮询订单状态、准备物流/收货通知 | 实测需要 `mobile` 和 `status`；旧文档只写 `userId` 不够 |
| 订单物流详情 | `order-user-delivery` | `GET` | `/app-api/mcp/api-mcp/orderUserdelivery` | `orderId` | 无 | 查询单个订单物流详情 | 需要先从订单接口拿到订单 ID |
| IM 群列表 | `im-group-list` | `GET` | `/prod-api/system/api/im/groupList` | `pageNo`、`pageSize` | 无 | 群发目标来源 | 返回里有 `id` 和 `gid`；发送群消息必须使用数字 `id`，`gid` 是微信 chatroom 标识，只用于排查 |
| 发送单人消息 | `send-chat-message` | `GET` | `/prod-api/system/api/im/sendChatMesage` | `mobile`、`content` | 无 | 私发早安问候、活动通知、订单/物流提醒 | 会真实发送，自动化脚本默认 dry-run，必须显式 `--execute` |
| 发送群消息 | `send-group-message` | `GET` | `/prod-api/system/api/im/sendGroupMesage` | `groupId`、`content` | 无 | 蔬菜推送、直播提醒、活动群提醒 | 会真实发送；`groupId` 必须使用 IM 群列表返回的数字 `id`，不能用 `gid` 或会员分组 `groupId` |

## 自动化任务覆盖表

| 文档任务 | 当前策略 | 依赖接口/能力 | 当前状态 |
| --- | --- | --- | --- |
| 6:00 公众号新闻转发 | 暂不处理 | 公众号素材/文章 API | 本阶段跳过 |
| 8:30 私发问候与产品提醒 | 会员列表 + 私发；天气/节日文案由 OpenClaw 搜索或外部内容生成后传入 | `member-user-list`、`send-chat-message`、OpenClaw 搜索 | 可执行 |
| 10:00 每日蔬菜品种推送 | 搜索蔬菜商品，生成群发文案 | `product-list`、`im-group-list`、`send-group-message` | 可执行 |
| 14:00 养生小知识推送 | 暂不处理 | 养生内容源/直播内容源 | 本阶段跳过 |
| 直播前提醒 | 读取预告，生成群发文案 | `yugao-list`、`im-group-list`、`send-group-message` | 可执行；福利亮点不足时需人工覆盖文案 |
| 17:30 直播二次提醒 | 同上，使用不同 phase 文案 | `yugao-list`、`im-group-list`、`send-group-message` | 可执行 |
| 18:00 直播链接提醒 | 同上，若接口无直播链接则只能发提醒文案 | `yugao-list`、`im-group-list`、`send-group-message` | 部分可执行 |
| 物流信息通知 | 主动轮询会员订单状态，再私发 | `member-user-list`、`member-user-order-list`、`order-user-delivery`、`send-chat-message` | 可执行，但需确认订单状态枚举含义 |
| 收货与评价提醒 | 轮询已签收/完成类状态，再私发 | `member-user-list`、`member-user-order-list`、`send-chat-message` | 可执行，但需确认订单状态枚举含义 |
| 活动开始/期间/最后一天通知 | 人工或配置文案 + 群发/私发 | `member-user-list`、`im-group-list`、`send-chat-message`、`send-group-message` | 可执行 |
| 每日收尾检查 | 汇总脚本 dry-run/execute 输出和发送结果 | 本地状态文件、命令输出 | 可执行 |

## 自动化脚本命令

脚本路径：`scripts/sudan_daily_automation.py`。默认都是 dry-run，不会真实发送。

| 命令 | 用途 | 示例 |
| --- | --- | --- |
| `api-check` | 只读检查核心 API 是否可用 | `python scripts/sudan_daily_automation.py api-check` |
| `vegetable-push` | 生成/发送每日蔬菜群推送 | `python scripts/sudan_daily_automation.py vegetable-push --group-limit 3` |
| `live-reminder` | 生成/发送直播提醒 | `python scripts/sudan_daily_automation.py live-reminder --phase pre --group-limit 3` |
| `private-greeting` | 生成/发送私发早安问候 | `python scripts/sudan_daily_automation.py private-greeting --member-limit 10 --weather-text "今日晴，18-28℃，早晚稍凉。"` |
| `order-scan` | 轮询订单状态并准备私发通知 | `python scripts/sudan_daily_automation.py order-scan --member-limit 20 --statuses 2,3,4` |

真实发送必须加 `--execute`：

| 场景 | 命令示例 |
| --- | --- |
| 给前 3 个群真实发送蔬菜推送 | `python scripts/sudan_daily_automation.py vegetable-push --group-limit 3 --execute` |
| 给前 10 个会员真实发送早安问候 | `python scripts/sudan_daily_automation.py private-greeting --member-limit 10 --content "早安～今天也记得照顾好自己。" --execute` |
| 订单轮询并真实发送通知 | `python scripts/sudan_daily_automation.py order-scan --member-limit 20 --statuses 2,3,4 --execute` |

## 待后续确认

| 项目 | 当前情况 | 影响 |
| --- | --- | --- |
| 订单 `status` 枚举含义 | 已能按 `status` 查询，但枚举业务语义未在仓库文档中完整确认 | 影响发货、中转、即将送达、签收、评价提醒的精确文案 |
| 直播链接字段 | `yugao-list` 当前返回 title/name/openTime 等信息，是否包含可直接发给用户的直播入口需继续确认 | 影响 18:00 直播链接推送 |
| 天气/节日来源 | 用户确认可走 OpenClaw 搜索 | 自动化脚本支持把搜索结果文案作为参数传入 |
| 公众号新闻 | 本阶段先不处理 | 6:00 新闻转发暂不进入自动化 |
| 养生知识 | 本阶段先不处理 | 14:00 养生推送暂不进入自动化 |
