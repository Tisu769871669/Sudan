from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    generated_dir = root / "distill" / "colleague-skill-generated" / "sudan_service"
    persona_path = generated_dir / "persona.md"
    work_path = generated_dir / "work.md"
    output_path = root / "persona" / "COLLEAGUE_SKILL_V2.md"

    if not persona_path.exists() or not work_path.exists():
        raise SystemExit(
            "Missing colleague-skill distillation output. "
            "Expected distill/colleague-skill-generated/sudan_service/{persona,work}.md"
        )

    persona_content = persona_path.read_text(encoding="utf-8").strip()
    work_content = work_path.read_text(encoding="utf-8").strip()

    merged = [
        "# Colleague-Skill V2",
        "",
        "以下内容来自 `colleague-skill` 官方结构产物的 v2 蒸馏结果。",
        "它用于补充当前线上客服的人格、承接方式和业务处理习惯。",
        "",
        "## Persona",
        "",
        persona_content,
        "",
        "## Work",
        "",
        work_content,
        "",
    ]

    output_path.write_text("\n".join(merged), encoding="utf-8")
    print(f"Synced: {output_path}")


if __name__ == "__main__":
    main()
