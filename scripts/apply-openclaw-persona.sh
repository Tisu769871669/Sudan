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

detect_config_path() {
  local reported=""

  if command -v openclaw >/dev/null 2>&1; then
    reported="$(openclaw config path 2>/dev/null || true)"
    if [[ -n "$reported" ]]; then
      reported="$(printf '%s\n' "$reported" | grep -Eo '/[^[:space:]]+\.(yaml|yml|json)' | tail -n 1 || true)"
      if [[ -n "$reported" && -f "$reported" ]]; then
        printf '%s\n' "$reported"
        return
      fi
    fi
  fi

  for path in \
    "$HOME/.openclaw/openclaw.yaml" \
    "$HOME/.openclaw/config.yaml" \
    "$HOME/.openclaw/openclaw.json" \
    "$HOME/.config/openclaw/config.json"
  do
    if [[ -f "$path" ]]; then
      printf '%s\n' "$path"
      return
    fi
  done

  echo "未找到 OpenClaw 配置文件。" >&2
  exit 1
}

main() {
  if ! command -v openclaw >/dev/null 2>&1; then
    echo "缺少 openclaw 命令，请先完成 OpenClaw 安装。" >&2
    exit 1
  fi

  local py_bin
  py_bin="$(choose_python)"

  "$py_bin" "$ROOT_DIR/build/compose-system-prompt.py"

  if [[ ! -f "$GENERATED_PROMPT" ]]; then
    echo "未生成 system_prompt.md。" >&2
    exit 1
  fi

  local config_path
  config_path="$(detect_config_path)"
  local backup_path
  backup_path="${config_path}.bak.$(date +%Y%m%d-%H%M%S)"
  cp "$config_path" "$backup_path"

  OPENCLAW_CONFIG_PATH="$config_path" \
  GENERATED_PROMPT_PATH="$GENERATED_PROMPT" \
  "$py_bin" - <<'PY'
from pathlib import Path
import json
import os
import sys

config_path = Path(os.environ["OPENCLAW_CONFIG_PATH"])
prompt_path = Path(os.environ["GENERATED_PROMPT_PATH"])
prompt_text = prompt_path.read_text(encoding="utf-8").strip()
suffix = config_path.suffix.lower()

if suffix in {".yaml", ".yml"}:
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise SystemExit("当前环境缺少 PyYAML，请先运行 scripts/prepare-server.sh") from exc

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit("OpenClaw 配置不是对象结构，无法更新。")

    agents = data.get("agents")
    if isinstance(agents, dict):
        main_agent = agents.setdefault("main", {})
        if not isinstance(main_agent, dict):
            raise SystemExit("agents.main 不是对象结构，无法更新。")
        main_agent["system_prompt"] = prompt_text
    elif isinstance(data.get("agent"), dict):
        data["agent"]["system_prompt"] = prompt_text
    else:
        data.setdefault("agents", {})
        data["agents"]["main"] = {"system_prompt": prompt_text}

    config_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
elif suffix == ".json":
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("OpenClaw 配置不是对象结构，无法更新。")

    agents = data.get("agents")
    if isinstance(agents, dict):
      main_agent = agents.setdefault("main", {})
      if not isinstance(main_agent, dict):
          raise SystemExit("agents.main 不是对象结构，无法更新。")
      main_agent["system_prompt"] = prompt_text
    elif isinstance(data.get("agent"), dict):
      data["agent"]["system_prompt"] = prompt_text
    else:
      data["agents"] = {"main": {"system_prompt": prompt_text}}

    config_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
else:
    raise SystemExit(f"不支持的配置格式: {config_path}")
PY

  echo "已备份配置: $backup_path"
  echo "正在校验 OpenClaw 配置..."
  openclaw config validate

  echo "正在重启 OpenClaw 网关..."
  if ! openclaw gateway restart; then
    echo "网关重启失败。可用以下命令回滚：" >&2
    echo "cp '$backup_path' '$config_path' && openclaw config validate && openclaw gateway restart" >&2
    exit 1
  fi

  echo "部署完成。"
  echo "配置文件: $config_path"
  echo "备份文件: $backup_path"
}

main "$@"
