# Sudan OpenClaw Persona Project

这个仓库用于维护“苏丹”专属客服在 OpenClaw 中的可部署人格配置，以及后续可导入的 FAQ 知识包。

## 目录结构

- `persona/`：人设源文件，按身份、风格、规则、开场话术拆分维护。
- `build/compose-system-prompt.py`：将 `persona/` 下的源文件合并为最终系统提示词。
- `build/generated/system_prompt.md`：合并后的最终 prompt，可直接写入 OpenClaw `system_prompt`。
- `knowledge/faq-source.txt`：原始 FAQ 素材。
- `knowledge/faq.md`：整理后的 FAQ 文档。
- `knowledge/faq.json`：结构化 FAQ，可供后续知识库导入。
- `node-services/agent-bridge/`：把第三方 HTTP `POST` 请求桥接到 OpenClaw `main` agent 的服务。
- `scripts/prepare-server.sh`：在 Linux 服务器上准备 Python 虚拟环境并安装依赖。
- `scripts/apply-openclaw-persona.sh`：生成 prompt、定位 OpenClaw 配置、备份、覆盖、校验并重启。
- `scripts/install-openclaw-service.sh`：当 OpenClaw 自带 `gateway install` 失效时，安装 systemd 兜底服务。
- `scripts/install-agent-bridge-service.sh`：把 `node-services/agent-bridge` 安装成 systemd 服务。
- `scripts/push-to-github.sh`：本地初始化 Git、提交并推送到 GitHub。

## 本地生成最终 prompt

```bash
python build/compose-system-prompt.py
```

## 推送到 GitHub

### Bash

```bash
cd /path/to/Sudan
bash scripts/push-to-github.sh
```

### PowerShell

```powershell
cd D:\Study\codeXprojection\苏丹小龙虾
git init
git branch -M main
git remote remove origin 2>$null
git remote add origin https://github.com/Tisu769871669/Sudan.git
git add .
git commit -m "feat: add Sudan OpenClaw persona project"
git push -u origin main
```

## Linux 服务器拉取并部署

```bash
cd ~
rm -rf Sudan
git clone https://github.com/Tisu769871669/Sudan.git
cd Sudan
bash scripts/prepare-server.sh
bash scripts/apply-openclaw-persona.sh
```

## HTTP Bridge

桥接服务目录：

```bash
node-services/agent-bridge
```

### 准备环境变量

```bash
cd ~/Sudan/node-services/agent-bridge
cp .env.example .env
```

至少修改这些值：

```env
AGENT_BRIDGE_TOKEN=replace_me
DEFAULT_AGENT_ID=main
OPENCLAW_BIN=openclaw
KNOWLEDGE_FILE=../../knowledge/faq.json
```

### 前台启动

```bash
cd ~/Sudan/node-services/agent-bridge
node src/server.js
```

### 安装为 systemd 服务

```bash
cd ~/Sudan
bash scripts/install-agent-bridge-service.sh
systemctl status openclaw-agent-bridge.service --no-pager
```

## Nginx HTTPS

如果要用 `sdseoul.metast.cn` 走 HTTPS，并把 443 反代到 bridge 的 9070，可直接执行：

```bash
cd ~/Sudan
bash scripts/install-nginx-https.sh
```

默认参数：

```env
DOMAIN=sdseoul.metast.cn
BRIDGE_PORT=9070
CERT_URL=https://getssl.vx.link/66a9a94fbae44.crt
KEY_URL=https://getssl.vx.link/66a9a94fbae44.key
```

执行后会：

- 安装 nginx
- 下载证书和私钥到 `/etc/nginx/ssl/`
- 写入站点配置
- 让 `443 -> 127.0.0.1:9070`
- 自动执行 `nginx -t` 和 `systemctl restart nginx`

站点配置模板在 `deploy/nginx/sdseoul.metast.cn.conf`

### 证书自动更新

仓库里附带了微林证书更新脚本：

```bash
cd ~/Sudan
bash scripts/update-vxssl.sh
```

可按微林文档加到 crontab，例如每天凌晨执行：

```bash
(crontab -l 2>/dev/null; echo "0 0 * * * /root/Sudan/scripts/update-vxssl.sh >> /var/log/update-vxssl.log 2>&1") | crontab -
```

### 健康检查

```bash
curl -sS http://127.0.0.1:9070/health
```

### 本机聊天测试

```bash
curl -sS -X POST http://127.0.0.1:9070/api/agents/chat \
  -H "Authorization: Bearer replace_me" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data-binary '{
    "conversationId": "test_001",
    "content": "黄精适合哪些人群吃？"
  }'
```

### 个微推荐请求格式

```json
{
  "conversationId": "wechat_user_001",
  "content": {
    "messageList": [
      { "role": "assistant", "text": "您好，我在这边。" },
      { "role": "user", "text": "介绍一下你能做什么" }
    ]
  }
}
```

## 部署脚本行为

- 优先把人格文件部署到 OpenClaw `main` agent 的 workspace。
- 会写入这些文件：
  - `SOUL.md`
  - `IDENTITY.md`
  - `STYLE.md`
  - `RULES.md`
  - `OPENING.md`
  - `AGENTS.md`
  - `knowledge/faq.md`
  - `knowledge/faq.json`
- 优先尝试 `openclaw config path` 查找配置文件。
- 优先尝试 `openclaw agents list` 查找 `main` agent 的 workspace。
- 若命令不可用或未返回有效路径，依次回退检查：
  - `~/.openclaw/openclaw.yaml`
  - `~/.openclaw/config.yaml`
  - `~/.openclaw/openclaw.json`
  - `~/.config/openclaw/config.json`
- 如果检测到旧版单 agent 配置结构，会额外更新配置中的 `system_prompt`。
- 如果检测到新版 `openclaw.json` 的 `agents.list` 结构，则不强改配置，只部署 workspace 文件，避免写出无效配置。
- 只有在脚本实际改动配置文件时，才会自动备份并执行 `openclaw config validate`。
- 最后执行 `openclaw gateway restart`。
- 如果返回 `Gateway service disabled`，部署脚本会自动尝试执行 `scripts/install-openclaw-service.sh` 作为 systemd 兜底服务安装。
- 如果自动安装失败，可以手动执行：
  - `bash scripts/install-openclaw-service.sh`
  - `systemctl status openclaw-gateway.service --no-pager`

## 回滚命令

```bash
cp /path/to/openclaw-config.bak.TIMESTAMP /path/to/openclaw-config
openclaw config validate
openclaw gateway restart
```

## OpenClaw 配置说明

OpenClaw 官方配置文档显示主配置文件通常位于 `~/.openclaw/openclaw.yaml`，并通过 `agents.<name>.system_prompt` 定义人格配置：

- [OpenClaw Configuration](https://openclawdoc.com/docs/getting-started/configuration/)

官方 FAQ 又提到 `openclaw config path` 以及历史 JSON 路径，因此部署脚本采用“CLI 探测优先 + 固定路径回退”的方式：

- [OpenClaw FAQ](https://openclawdoc.com/faq/)
