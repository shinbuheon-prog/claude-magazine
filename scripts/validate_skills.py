"""
Claude Code Skills 검증 스크립트 (TASK_030 보강)

.claude/skills/ 하위 모든 SKILL.md를 검사:
1. frontmatter 유효성 (name, description, allowed-tools 필수)
2. 필수 섹션 존재 (언제 사용, 절차, Verify before success)
3. Bash 명령 참조 파일 실재 여부 (정적 분석)
4. name 필드와 폴더명 일치

사용법:
    python scripts/validate_skills.py
    python scripts/validate_skills.py --strict
"""
import argparse
import re
import sys
from pathlib import Path

# Windows UTF-8 출력 강제
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / ".claude" / "skills"

REQUIRED_FRONTMATTER_KEYS = {"name", "description", "allowed-tools"}
REQUIRED_SECTIONS = ["## 언제 사용", "## 절차", "## Verify before success"]


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """YAML frontmatter 파싱 (간이). 반환: (dict, body_markdown)"""
    if not text.startswith("---"):
        return {}, text

    end_match = re.search(r"\n---\n", text[3:])
    if not end_match:
        return {}, text

    fm_text = text[3 : end_match.start() + 3]
    body = text[end_match.end() + 3 :]

    result = {}
    for line in fm_text.strip().split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()

    return result, body


def extract_bash_commands(body: str) -> list[str]:
    """본문에서 ```bash ... ``` 블록 내 명령 추출"""
    pattern = re.compile(r"```bash\s*\n(.*?)\n```", re.DOTALL)
    commands = []
    for match in pattern.finditer(body):
        for line in match.group(1).split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                commands.append(stripped)
    return commands


def validate_skill(skill_path: Path) -> dict:
    """단일 SKILL.md 검증"""
    name = skill_path.parent.name
    result = {
        "name": name,
        "path": str(skill_path.relative_to(ROOT)),
        "errors": [],
        "warnings": [],
    }

    if not skill_path.exists():
        result["errors"].append("SKILL.md 파일 없음")
        return result

    text = skill_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    # 1. frontmatter 유효성
    missing_keys = REQUIRED_FRONTMATTER_KEYS - set(fm.keys())
    if missing_keys:
        result["errors"].append(f"frontmatter 누락: {sorted(missing_keys)}")

    # 2. name 필드와 폴더명 일치
    if "name" in fm and fm["name"] != name:
        result["errors"].append(f"name 불일치: frontmatter={fm['name']}, 폴더={name}")

    # 3. 필수 섹션
    for section in REQUIRED_SECTIONS:
        # 부분 매칭 (예: "## 절차 (Systematic)"도 "## 절차"로 매칭)
        section_key = section.replace("## ", "")
        if not re.search(rf"^##\s+{re.escape(section_key)}", body, re.MULTILINE):
            result["errors"].append(f"섹션 누락: {section}")

    # 4. description 길이 (자동 트리거 위해 중요)
    if "description" in fm:
        desc_len = len(fm["description"])
        if desc_len < 20:
            result["warnings"].append(f"description 짧음 ({desc_len}자) — 자동 트리거 정확도 낮을 수 있음")
        if desc_len > 250:
            result["warnings"].append(f"description 김 ({desc_len}자) — 250자 이내 권장")

    # 5. Bash 명령에서 참조하는 파일 존재 여부 (정적)
    commands = extract_bash_commands(body)
    for cmd in commands:
        # python pipeline/X.py 또는 python scripts/X.py 패턴
        match = re.search(r"python\s+(pipeline/[\w_]+\.py|scripts/[\w_]+\.py)", cmd)
        if match:
            ref_file = ROOT / match.group(1)
            if not ref_file.exists():
                result["warnings"].append(f"참조 파일 없음: {match.group(1)}")

    return result


def validate_language_adaptation(body: str, lang: str) -> list[str]:
    warnings: list[str] = []
    if lang == "ko":
        if not re.search(r"[가-힣]", body):
            warnings.append("한국어 적응 부족: 본문에 한글이 거의 없음")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Claude Code Skills 검증")
    parser.add_argument("--strict", action="store_true", help="경고도 실패로 간주")
    parser.add_argument("--skill", help="특정 skill 폴더명만 검사")
    parser.add_argument("--lang", choices=["ko"], help="언어 적응 검사")
    args = parser.parse_args()

    if not SKILLS_DIR.exists():
        print(f"❌ Skills 폴더 없음: {SKILLS_DIR}", file=sys.stderr)
        return 1

    skill_dirs = sorted([d for d in SKILLS_DIR.iterdir() if d.is_dir()])
    if args.skill:
        skill_dirs = [d for d in skill_dirs if d.name == args.skill]
    if not skill_dirs:
        print(f"⚠️  Skills 폴더 비어있음: {SKILLS_DIR}")
        return 0

    print(f"=== Claude Code Skills 검증 ({len(skill_dirs)}개) ===\n")

    total_errors = 0
    total_warnings = 0

    for idx, skill_dir in enumerate(skill_dirs, 1):
        skill_md = skill_dir / "SKILL.md"
        result = validate_skill(skill_md)
        if args.lang:
            result["warnings"].extend(validate_language_adaptation(skill_md.read_text(encoding="utf-8"), args.lang))

        status_icon = "✅"
        if result["errors"]:
            status_icon = "❌"
        elif result["warnings"]:
            status_icon = "⚠️"

        print(f"[{idx}/{len(skill_dirs)}] {status_icon} {result['name']}")
        print(f"       {result['path']}")

        for err in result["errors"]:
            print(f"       ERROR: {err}")
            total_errors += 1

        for warn in result["warnings"]:
            print(f"       WARN:  {warn}")
            total_warnings += 1

        print()

    print(f"=== 결과: {len(skill_dirs)}개 검사 / {total_errors} 오류 / {total_warnings} 경고 ===")

    if total_errors > 0:
        return 1
    if args.strict and total_warnings > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
