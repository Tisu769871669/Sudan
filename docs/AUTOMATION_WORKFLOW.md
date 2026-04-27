# 苏丹客服自动化工作流程维护文档

本文档说明苏丹客服每日自动化脚本如何运行、如何测试、如何配置 cron 定时任务，以及后续维护时需要注意哪些边界。它面向服务器维护者和运营同学，尽量把命令、风险点和排查路径写清楚。

相关文档：

- `docs/API_REFERENCE.md`：接口能力和参数说明。
- `MAINTENANCE.md`：项目整体维护、部署和排障说明。
- `skills/metast-mcp/SKILL.md`：OpenClaw agent 使用 Metast MCP 能力时的操作规则。

## 1. 当前自动化覆盖范围

自动化入口脚本：

```bash
scripts/sudan_daily_automation.py
```

脚本默认都是 dry-run，只生成计划和预览，不会真实发送。只有显式加 `--execute` 才会调用真实发送接口。

| 业务时间 | 任务 | 脚本命令 | 当前状态 | 说明 |
| --- | --- | --- | --- | --- |
| 每日巡检 | 接口连通性检查 | `api-check` | 可执行 | 只读，不发消息 |
| 8:30 | 私发早安问候 | `private-greeting` | 可执行 | 天气/节日文案需要外部生成后传入 |
| 10:00 | 每日蔬菜群推送 | `vegetable-push` | 可执行 | 会先查商品，再群发 |
| 直播前 | 直播预告提醒 | `live-reminder --phase pre` | 可执行 | 使用预告接口生成提醒 |
| 17:30 | 直播二次提醒 | `live-reminder --phase final` | 可执行 | 同一个直播预告，不同文案阶段 |
| 18:00 | 直播入口提醒 | `live-reminder --phase link` | 部分可执行 | 当前接口若没有直播链接，只能发入口提醒文案 |
| 白天轮询 | 物流/订单状态通知 | `order-scan` | 可执行但需灰度 | 订单状态枚举还需要业务确认 |
| 6:00 | 公众号新闻转发 | 暂不处理 | 本阶段跳过 | 用户已确认先不做公众号养生 |
| 14:00 | 养生知识推送 | 暂不处理 | 本阶段跳过 | 后续有内容源后再接 |

## 2. 运行前准备

在服务器上进入项目目录：

```bash
cd /root/Sudan
```

确认 `.env.metast` 存在，并包含：

```env
METAST_MCP_BASE_URL=https://lx.metast.cn
METAST_MCP_KEY=你的 key
METAST_MCP_SECRET=你的 secret
```

凭证不要提交到 GitHub。脚本会按以下顺序查找凭证：

1. `METAST_MCP_ENV_FILE`
2. 当前项目目录 `.env.metast`
3. 当前工作目录 `.env.metast`
4. `~/Sudan/.env.metast`
5. `~/.openclaw/.env.metast`

建议先跑：

```bash
python3 -m py_compile scripts/sudan_daily_automation.py skills/metast-mcp/scripts/fetch_metast_mcp.py
python3 scripts/sudan_daily_automation.py api-check
```

`api-check` 只检查只读接口，不会发消息。

## 3. 命令说明

### 3.1 接口检查

```bash
python3 scripts/sudan_daily_automation.py api-check
```

检查内容：

- 直播/预告列表。
- 商品列表。
- 会员列表。
- IM 群列表。

看到每项有 `records` 和 `keys` 即说明接口基本可用。这个命令适合放到每天早上的巡检 cron。

### 3.2 蔬菜群推送

dry-run：

```bash
python3 scripts/sudan_daily_automation.py vegetable-push \
  --group-limit 1 \
  --content "【内部测试】苏丹客服自动化群发测试，收到可忽略。"
```

真实发送：

```bash
python3 scripts/sudan_daily_automation.py vegetable-push \
  --group-limit 1 \
  --content "【内部测试】苏丹客服自动化群发测试，收到可忽略。" \
  --execute
```

维护要点：

- `groupId` 必须是 `im-group-list` 返回的数字 `id`。
- `gid` 类似 `53220657641@chatroom`，只用于排查，不能传给发送接口。
- `--group-limit 1` 适合灰度测试，确认成功后再逐步放大。
- 不传 `--content` 时，脚本会根据商品接口返回的蔬菜商品生成简短群发文案。

### 3.3 直播提醒

直播提醒有三个阶段：

```bash
python3 scripts/sudan_daily_automation.py live-reminder --phase pre --group-limit 1
python3 scripts/sudan_daily_automation.py live-reminder --phase final --group-limit 1
python3 scripts/sudan_daily_automation.py live-reminder --phase link --group-limit 1
```

真实发送时加 `--execute`：

```bash
python3 scripts/sudan_daily_automation.py live-reminder --phase pre --group-limit 1 --execute
```

阶段说明：

| phase | 建议时间 | 文案含义 |
| --- | --- | --- |
| `pre` | 直播前较早时间 | “今天有直播提醒，别错过” |
| `final` | 直播前半小时左右 | “直播马上开始” |
| `link` | 直播开始时 | “直播入口已经准备好了” |

如果运营需要固定福利点、主播话术或直播链接，优先用 `--content` 人工覆盖：

```bash
python3 scripts/sudan_daily_automation.py live-reminder \
  --phase link \
  --group-limit 1 \
  --content "今晚 18:00 直播开始，入口已经准备好了，方便的话可以进来看看。" \
  --execute
```

### 3.4 私发早安问候

dry-run：

```bash
python3 scripts/sudan_daily_automation.py private-greeting \
  --member-limit 1 \
  --weather-text "今日晴，早晚稍凉。"
```

真实发送：

```bash
python3 scripts/sudan_daily_automation.py private-greeting \
  --member-limit 1 \
  --weather-text "今日晴，早晚稍凉。" \
  --execute
```

可选参数：

| 参数 | 用途 |
| --- | --- |
| `--weather-text` | 天气提示，例如“今日晴，早晚稍凉。” |
| `--holiday-text` | 节日、节气、纪念日提示 |
| `--content` | 完全覆盖为一条固定文案 |
| `--content-file` | 从文件读取固定文案 |
| `--member-limit` | 限制会员数量，`0` 表示全部 |

关于天气和节日：

- 当前脚本不会自己联网查天气。
- 用户已确认天气/节日可以交给 OpenClaw 搜索或外部流程生成。
- cron 全自动运行时，建议先把当天文案写入一个本地文件，再由 cron 读取传给脚本。

示例：

```bash
mkdir -p /root/Sudan/.runtime
echo "今日晴，早晚稍凉。" > /root/Sudan/.runtime/weather.txt

python3 scripts/sudan_daily_automation.py private-greeting \
  --member-limit 1 \
  --weather-text "$(cat /root/Sudan/.runtime/weather.txt)"
```

### 3.5 订单状态轮询

dry-run：

```bash
python3 scripts/sudan_daily_automation.py order-scan \
  --member-limit 1 \
  --statuses 0,1,2,3,4
```

真实发送：

```bash
python3 scripts/sudan_daily_automation.py order-scan \
  --member-limit 1 \
  --statuses 2,3,4 \
  --execute
```

维护要点：

- `member-user-order-list` 实测需要 `mobile` 和 `status`。
- `status` 枚举业务含义还没有完整确认，不建议一开始全量执行。
- 脚本会把已通知订单写到 `.automation-state/order-notifications.json`，避免重复通知。
- `.automation-state/` 已被 `.gitignore` 忽略，不应提交。

状态文案当前逻辑：

| status | 当前脚本文案倾向 |
| --- | --- |
| `2` 或 `20` | 物流有更新 |
| `3` 或 `30` | 快到/已到附近，提醒签收 |
| `4` 或 `40` | 已签收，提醒检查包裹 |
| 其他 | 状态有更新 |

上线前必须用真实订单确认后端状态枚举，否则容易把“待付款、待发货、已取消”等状态误发成物流提醒。

## 4. 推荐测试流程

每次改脚本或上线前按这个顺序走：

```bash
python3 -m py_compile scripts/sudan_daily_automation.py scripts/sudan_daily_automation_test.py skills/metast-mcp/scripts/fetch_metast_mcp.py
python3 scripts/sudan_daily_automation_test.py
python3 skills/metast-mcp/scripts/fetch_metast_mcp_test.py
python3 scripts/sudan_daily_automation.py api-check
```

再分别 dry-run：

```bash
python3 scripts/sudan_daily_automation.py vegetable-push --group-limit 1
python3 scripts/sudan_daily_automation.py live-reminder --phase pre --group-limit 1
python3 scripts/sudan_daily_automation.py private-greeting --member-limit 1 --weather-text "今日晴，早晚稍凉。"
python3 scripts/sudan_daily_automation.py order-scan --member-limit 1 --statuses 0,1,2,3,4
```

确认 dry-run 输出：

- `mode` 是 `dry-run`。
- `executed` 是 `false`。
- `groupId` 是数字 ID，不是 `@chatroom`。
- 文案没有错别字、敏感承诺或错误直播时间。
- `targetCount` 符合预期。

真实发送建议分三步：

1. 内部测试群或内部手机号，`--group-limit 1` / `--member-limit 1`。
2. 小范围灰度，扩大到 3 到 10 个目标。
3. 全量执行，`--group-limit 0` / `--member-limit 0`。

## 5. cron 定时任务建议

可以设定为 cron 任务，但建议先 dry-run 一周，确认日志和目标都正确，再打开 `--execute`。

准备日志目录：

```bash
sudo mkdir -p /var/log/sudan-automation
sudo touch /var/log/sudan-automation/api-check.log
sudo touch /var/log/sudan-automation/vegetable-push.log
sudo touch /var/log/sudan-automation/live-reminder.log
sudo touch /var/log/sudan-automation/private-greeting.log
sudo touch /var/log/sudan-automation/order-scan.log
```

编辑 root crontab：

```bash
sudo crontab -e
```

### 5.1 灰度期 cron 模板

灰度期不建议全量真实发送。可以先用 `--group-limit 1`、`--member-limit 1`，并尽量发到内部测试群或内部手机号。

```cron
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
SUDAN_DIR=/root/Sudan
LOG_DIR=/var/log/sudan-automation

# 每天 08:00 只读接口巡检
0 8 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-api-check.lock python3 scripts/sudan_daily_automation.py api-check >> $LOG_DIR/api-check.log 2>&1

# 每天 08:30 私发早安问候，灰度 1 人
30 8 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-private-greeting.lock python3 scripts/sudan_daily_automation.py private-greeting --member-limit 1 --weather-text "$(cat /root/Sudan/.runtime/weather.txt 2>/dev/null)" >> $LOG_DIR/private-greeting.log 2>&1

# 每天 10:00 蔬菜群推送，灰度 1 个群
0 10 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-vegetable-push.lock python3 scripts/sudan_daily_automation.py vegetable-push --group-limit 1 >> $LOG_DIR/vegetable-push.log 2>&1

# 直播前提醒，灰度 1 个群
0 17 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-live-pre.lock python3 scripts/sudan_daily_automation.py live-reminder --phase pre --group-limit 1 >> $LOG_DIR/live-reminder.log 2>&1
30 17 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-live-final.lock python3 scripts/sudan_daily_automation.py live-reminder --phase final --group-limit 1 >> $LOG_DIR/live-reminder.log 2>&1
0 18 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-live-link.lock python3 scripts/sudan_daily_automation.py live-reminder --phase link --group-limit 1 >> $LOG_DIR/live-reminder.log 2>&1

# 订单轮询先 dry-run，不建议未确认状态枚举前直接 execute
0 11,15,19 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-order-scan.lock python3 scripts/sudan_daily_automation.py order-scan --member-limit 1 --statuses 2,3,4 >> $LOG_DIR/order-scan.log 2>&1
```

### 5.2 正式执行 cron 模板

确认灰度稳定后，再加 `--execute`。全量发送要把 limit 改成 `0`。

```cron
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
SUDAN_DIR=/root/Sudan
LOG_DIR=/var/log/sudan-automation

0 8 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-api-check.lock python3 scripts/sudan_daily_automation.py api-check >> $LOG_DIR/api-check.log 2>&1
30 8 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-private-greeting.lock python3 scripts/sudan_daily_automation.py private-greeting --member-limit 0 --weather-text "$(cat /root/Sudan/.runtime/weather.txt 2>/dev/null)" --execute >> $LOG_DIR/private-greeting.log 2>&1
0 10 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-vegetable-push.lock python3 scripts/sudan_daily_automation.py vegetable-push --group-limit 0 --execute >> $LOG_DIR/vegetable-push.log 2>&1
0 17 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-live-pre.lock python3 scripts/sudan_daily_automation.py live-reminder --phase pre --group-limit 0 --execute >> $LOG_DIR/live-reminder.log 2>&1
30 17 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-live-final.lock python3 scripts/sudan_daily_automation.py live-reminder --phase final --group-limit 0 --execute >> $LOG_DIR/live-reminder.log 2>&1
0 18 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-live-link.lock python3 scripts/sudan_daily_automation.py live-reminder --phase link --group-limit 0 --execute >> $LOG_DIR/live-reminder.log 2>&1
```

订单轮询建议等状态枚举确认后再进入正式 cron：

```cron
0 11,15,19 * * * cd $SUDAN_DIR && /usr/bin/flock -n /tmp/sudan-order-scan.lock python3 scripts/sudan_daily_automation.py order-scan --member-limit 0 --statuses 2,3,4 --execute >> $LOG_DIR/order-scan.log 2>&1
```

## 6. 日志查看

```bash
tail -n 100 /var/log/sudan-automation/api-check.log
tail -n 100 /var/log/sudan-automation/vegetable-push.log
tail -n 100 /var/log/sudan-automation/live-reminder.log
tail -n 100 /var/log/sudan-automation/private-greeting.log
tail -n 100 /var/log/sudan-automation/order-scan.log
```

检查 cron 是否安装：

```bash
sudo crontab -l
```

检查 cron 服务：

```bash
systemctl status cron --no-pager
```

如果系统使用 `crond`：

```bash
systemctl status crond --no-pager
```

## 7. 安全边界

真实发送接口风险最高：

- `send-chat-message` 会真实私发用户。
- `send-group-message` 会真实发群。
- 所有群发/私发默认先 dry-run。
- cron 正式执行必须显式加 `--execute`。
- 灰度期间必须保留 `--group-limit 1` 或 `--member-limit 1`。

不要在文档、截图、日志里暴露：

- `METAST_MCP_KEY`
- `METAST_MCP_SECRET`
- `AGENT_BRIDGE_TOKEN`
- 用户手机号
- 原始聊天记录

如果误发：

1. 先停止 cron：`sudo crontab -e` 注释相关行。
2. 保存日志，不要覆盖现场。
3. 查具体命令、目标、文案和接口返回。
4. 需要时删除 `.automation-state/order-notifications.json` 中错误状态，但不要盲删整个文件。

## 8. 常见问题

| 现象 | 可能原因 | 处理方式 |
| --- | --- | --- |
| `Missing METAST_MCP_KEY or METAST_MCP_SECRET` | cron 环境没读到 `.env.metast` | 确认 `cd /root/Sudan`，或设置 `METAST_MCP_ENV_FILE=/root/Sudan/.env.metast` |
| 群发返回 Java Long 转换失败 | 把 `gid` 当成 `groupId` | 更新代码，确认 dry-run 的 `groupId` 是数字 |
| dry-run 有消息但没有真实发送 | 没有加 `--execute` | 确认目标和文案后再加 |
| 订单提醒重复 | 状态文件丢失或换了 `state-file` | 检查 `.automation-state/order-notifications.json` |
| 订单提醒不发 | 状态枚举不对或会员没有对应订单 | 用 `member-user-order-list` 单独查真实手机号和 status |
| 直播链接没有出现 | `yugao-list` 没返回链接字段 | 用 `--content` 人工覆盖直播链接 |
| 早安问候没有天气 | 没传 `--weather-text` 或天气文件为空 | 先写 `/root/Sudan/.runtime/weather.txt` |

## 9. 后续可优化项

- 增加独立 wrapper 脚本，把天气/节日搜索、文案审核和发送串起来。
- 给群发和私发增加白名单，避免误发到非测试群或非目标会员。
- 将订单状态枚举整理成固定配置文件，避免写死在命令里。
- 增加发送审计日志，记录任务、目标、内容摘要、接口返回和执行人。
- 把活动通知抽成配置文件，支持开始前、进行中、最后一天三段文案。
