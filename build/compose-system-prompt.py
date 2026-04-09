from pathlib import Path


SECTIONS = [
    "IDENTITY.md",
    "DISTILLED_SERVICE.md",
    "STYLE.md",
    "RULES.md",
    "OPENING.md",
]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    persona_dir = root / "persona"
    output_path = root / "build" / "generated" / "system_prompt.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    parts = [
        "# Sudan OpenClaw System Prompt",
        "",
        "以下内容由仓库中的人设源文件自动拼装生成，用于写入 OpenClaw 的 `system_prompt`。",
        "",
    ]

    for name in SECTIONS:
        content = (persona_dir / name).read_text(encoding="utf-8").strip()
        parts.append(content)
        parts.append("")

    output_path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
