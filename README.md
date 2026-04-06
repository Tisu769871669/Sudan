# Sudan OpenClaw Persona Project

这个仓库用于维护“苏丹”专属客服在 OpenClaw 中的可部署人格配置，以及后续可导入的 FAQ 知识包。

## 目录结构

- `persona/`：人设源文件，按身份、风格、规则、开场话术拆分维护。
- `build/compose-system-prompt.py`：将 `persona/` 下的源文件合并为最终系统提示词。
- `build/generated/system_prompt.md`：合并后的最终 prompt，可直接写入 OpenClaw `system_prompt`。
- `knowledge/faq-source.txt`：原始 FAQ 素材。
- `knowledge/faq.md`：整理后的 FAQ 文档。
- `knowledge/faq.json`：结构化 FAQ，可供后续知识库导入。
- `scripts/prepare-server.sh`：在 Linux 服务器上准备 Python 虚拟环境并安装依赖。
- `scripts/apply-openclaw-persona.sh`：生成 prompt、定位 OpenClaw 配置、备份、覆盖、校验并重启。
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

## 部署脚本行为

- 优先尝试 `openclaw config path` 查找配置文件。
- 若命令不可用或未返回有效路径，依次回退检查：
  - `~/.openclaw/openclaw.yaml`
  - `~/.openclaw/config.yaml`
  - `~/.openclaw/openclaw.json`
  - `~/.config/openclaw/config.json`
- 默认更新 `agents.main.system_prompt`。
- 如果检测到旧版单 agent 结构，会回退写入 `agent.system_prompt`。
- 写入前会自动备份原配置。
- 写入后执行 `openclaw config validate` 和 `openclaw gateway restart`。

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
