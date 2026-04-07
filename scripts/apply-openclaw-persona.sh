#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
GENERATED_PROMPT="$ROOT_DIR/build/generated/system_prompt.md"

choose_python() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    echo "$VENV_DIR/bin/python"
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi

  echo "未找到可用的 Python 解释器。" >&2
  exit 1
}

run_python() {
  local py_bin
  py_bin="$(choose_python)"
  "$py_bin" "$@"
}

copy_workspace_files() {
  local workspace_path="$1"

  mkdir -p "$workspace_path/knowledge"
  if [[ -f "$workspace_path/BOOTSTRAP.md" ]]; then
    mv "$workspace_path/BOOTSTRAP.md" "$workspace_path/BOOTSTRAP.md.disabled.$(date +%Y%m%d-%H%M%S)"
  fi
  cp "$ROOT_DIR/persona/IDENTITY.md" "$workspace_path/IDENTITY.md"
  cp "$ROOT_DIR/persona/STYLE.md" "$workspace_path/STYLE.md"
  cp "$ROOT_DIR/persona/RULES.md" "$workspace_path/RULES.md"
  cp "$ROOT_DIR/persona/OPENING.md" "$workspace_path/OPENING.md"
  cp "$ROOT_DIR/build/generated/system_prompt.md" "$workspace_path/SOUL.md"
  cp "$ROOT_DIR/knowledge/faq.md" "$workspace_path/knowledge/faq.md"
  cp "$ROOT_DIR/knowledge/faq.json" "$workspace_path/knowledge/faq.json"

  cat > "$workspace_path/AGENTS.md" <<'EOF'
# Workspace Rules

启动后优先参考以下文件：

1. `SOUL.md`
2. `IDENTITY.md`
3. `STYLE.md`
4. `RULES.md`
5. `OPENING.md`
6. `knowledge/faq.md`

行为要求：

- 你是苏丹的数字分身。
- 回复要有真人感，先答问题，再自然引导下一步。
- 知识库不匹配时不要硬答，复杂情况转人工客服。
- 不要出现“根据资料”“根据上下文”“系统显示”等机械表达。
- 涉及医疗、疗效、诊断时要克制，不做明确治疗承诺。
EOF
}

sync_openclaw_identity() {
  local workspace_path="$1"
  if command -v openclaw >/dev/null 2>&1; then
    openclaw agents set-identity --agent main --workspace "$workspace_path" --from-identity >/dev/null 2>&1 || \
    openclaw agents set-identity --agent main --from-identity >/dev/null 2>&1 || true
  fi
}

main() {
  if ! command -v openclaw >/dev/null 2>&1; then
    echo "缺少 openclaw 命令，请先完成 OpenClaw 安装。" >&2
    exit 1
  fi

  run_python "$ROOT_DIR/build/compose-system-prompt.py"

  if [[ ! -f "$GENERATED_PROMPT" ]]; then
    echo "未生成 system_prompt.md。" >&2
    exit 1
  fi

  local metadata_file
  metadata_file="$(mktemp)"

  METADATA_PATH="$metadata_file" run_python - <<'PY'
from pathlib import Path
import json
import os
import subprocess


def detect_config_path() -> Path | None:
    try:
        result = subprocess.run(
            ["openclaw", "config", "path"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = None

    if result and result.returncode == 0:
        for line in (result.stdout + "\n" + result.stderr).splitlines():
            line = line.strip()
            if line.startswith("/") and Path(line).suffix.lower() in {".yaml", ".yml", ".json"}:
                path = Path(line).expanduser()
                if path.exists():
                    return path

    for raw in [
        "~/.openclaw/openclaw.yaml",
        "~/.openclaw/config.yaml",
        "~/.openclaw/openclaw.json",
        "~/.config/openclaw/config.json",
    ]:
        path = Path(raw).expanduser()
        if path.exists():
            return path
    return None


def detect_workspace_from_agents_list() -> Path | None:
    try:
        result = subprocess.run(
            ["openclaw", "agents", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        return None

    current_agent = None
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            current_agent = stripped[2:].split()[0]
            continue
        if current_agent == "main" and stripped.startswith("Workspace:"):
            return Path(stripped.split(":", 1)[1].strip()).expanduser()
    return None


config_path = detect_config_path()
workspace_path = detect_workspace_from_agents_list() or Path("~/.openclaw/workspace").expanduser()
update_strategy = "workspace_only"

if config_path:
    suffix = config_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        import yaml

        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if isinstance(data.get("agent"), dict):
            workspace_path = Path(data["agent"].get("workspace", workspace_path)).expanduser()
            update_strategy = "yaml_single_agent"
        elif isinstance(data.get("agents"), dict) and "list" not in data["agents"] and isinstance(data["agents"].get("main"), dict):
            workspace_path = Path(data["agents"]["main"].get("workspace", workspace_path)).expanduser()
            update_strategy = "yaml_agents_mapping"
    elif suffix == ".json":
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(data.get("agent"), dict):
            workspace_path = Path(data["agent"].get("workspace", workspace_path)).expanduser()
            update_strategy = "json_single_agent"
        elif isinstance(data.get("agents"), dict):
            agents = data["agents"]
            if isinstance(agents.get("main"), dict):
                workspace_path = Path(agents["main"].get("workspace", workspace_path)).expanduser()
                update_strategy = "json_agents_mapping"
            elif isinstance(agents.get("list"), list):
                for item in agents["list"]:
                    if isinstance(item, dict) and item.get("id") == "main":
                        workspace_path = Path(item.get("workspace", workspace_path)).expanduser()
                        break
                defaults = agents.get("defaults", {})
                if isinstance(defaults, dict) and defaults.get("workspace"):
                    workspace_path = Path(defaults["workspace"]).expanduser()
                update_strategy = "workspace_only"

metadata = {
    "config_path": str(config_path) if config_path else "",
    "workspace_path": str(workspace_path),
    "update_strategy": update_strategy,
}
Path(os.environ["METADATA_PATH"]).write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
PY

  local workspace_path
  workspace_path="$(run_python -c "import json, pathlib; data=json.loads(pathlib.Path('$metadata_file').read_text(encoding='utf-8')); print(data['workspace_path'])")"
  local config_path
  config_path="$(run_python -c "import json, pathlib; data=json.loads(pathlib.Path('$metadata_file').read_text(encoding='utf-8')); print(data['config_path'])")"
  local update_strategy
  update_strategy="$(run_python -c "import json, pathlib; data=json.loads(pathlib.Path('$metadata_file').read_text(encoding='utf-8')); print(data['update_strategy'])")"

  local backup_path=""
  if [[ "$update_strategy" != "workspace_only" && -n "$config_path" ]]; then
    backup_path="${config_path}.bak.$(date +%Y%m%d-%H%M%S)"
    cp "$config_path" "$backup_path"

    OPENCLAW_CONFIG_PATH="$config_path" \
    GENERATED_PROMPT_PATH="$GENERATED_PROMPT" \
    UPDATE_STRATEGY="$update_strategy" \
    run_python - <<'PY'
from pathlib import Path
import json
import os

config_path = Path(os.environ["OPENCLAW_CONFIG_PATH"])
prompt_text = Path(os.environ["GENERATED_PROMPT_PATH"]).read_text(encoding="utf-8").strip()
strategy = os.environ["UPDATE_STRATEGY"]

if strategy.startswith("yaml_"):
    import yaml

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if strategy == "yaml_single_agent":
        data["agent"]["system_prompt"] = prompt_text
    elif strategy == "yaml_agents_mapping":
        data["agents"]["main"]["system_prompt"] = prompt_text
    else:
        raise SystemExit(f"未知 YAML 更新策略: {strategy}")

    config_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
elif strategy.startswith("json_"):
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if strategy == "json_single_agent":
        data["agent"]["system_prompt"] = prompt_text
    elif strategy == "json_agents_mapping":
        data["agents"]["main"]["system_prompt"] = prompt_text
    else:
        raise SystemExit(f"未知 JSON 更新策略: {strategy}")

    config_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
else:
    raise SystemExit(f"不支持的更新策略: {strategy}")
PY
  fi

  copy_workspace_files "$workspace_path"
  sync_openclaw_identity "$workspace_path"
  rm -f "$metadata_file"

  if [[ "$update_strategy" != "workspace_only" && -n "$config_path" ]]; then
    echo "已更新配置中的 system_prompt。"
    echo "配置备份: $backup_path"
    echo "正在校验 OpenClaw 配置..."
    openclaw config validate
  else
    echo "当前配置结构未直接写入 system_prompt，已改为部署到 workspace 文件。"
  fi

  echo "Workspace 已同步到: $workspace_path"
  echo "正在重启 OpenClaw 网关..."
  local restart_output
  if ! restart_output="$(openclaw gateway restart 2>&1)"; then
    printf '%s\n' "$restart_output"
    echo "网关重启失败。可用以下命令回滚：" >&2
    if [[ -n "$backup_path" && -n "$config_path" ]]; then
      echo "cp '$backup_path' '$config_path' && openclaw config validate && openclaw gateway restart" >&2
    else
      echo "请检查 workspace 文件和 OpenClaw 日志后重试。" >&2
    fi
    exit 1
  fi
  printf '%s\n' "$restart_output"

  if printf '%s\n' "$restart_output" | grep -qi "Gateway service disabled"; then
    echo "检测到 OpenClaw 内置的 gateway service 未启用，尝试安装 systemd 兜底服务..."
    if [[ "$(id -u)" -eq 0 && -f "$ROOT_DIR/scripts/install-openclaw-service.sh" ]]; then
      bash "$ROOT_DIR/scripts/install-openclaw-service.sh"
      echo "部署完成。"
      if [[ -n "$config_path" ]]; then
        echo "配置文件: $config_path"
      fi
      echo "Workspace: $workspace_path"
      exit 0
    fi

    echo "网关服务未启用，当前只完成了人格与知识文件部署。" >&2
    echo "请执行：bash scripts/install-openclaw-service.sh" >&2
    echo "如果只是临时前台启动，可直接执行：openclaw gateway" >&2
    exit 2
  fi

  echo "部署完成。"
  if [[ -n "$config_path" ]]; then
    echo "配置文件: $config_path"
  fi
  echo "Workspace: $workspace_path"
}

main "$@"
