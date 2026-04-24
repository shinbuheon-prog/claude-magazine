"""
본문에 baoyu article illustrator용 이미지 자산과 로그를 삽입한다.
실제 이미지 생성 백엔드가 없을 때는 placeholder PNG를 만든다.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ILLUSTRATION_ROOT = ROOT / "output" / "illustrations"
LOG_PATH = ROOT / "logs" / "illustrations.jsonl"


def _slugify(value: str, fallback: str) -> str:
    text = re.sub(r"[^\w\s-]", " ", value, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "-", text).strip("-").lower()
    return text[:60] or fallback


def _select_targets(markdown: str) -> list[tuple[str, str]]:
    sections = re.findall(r"^##\s+(.+)$", markdown, flags=re.MULTILINE)
    if sections:
        return [(title.strip(), "framework") for title in sections[:2]]
    return [("핵심 요약", "infographic")]


def _write_prompt(prompt_path: Path, title: str, image_type: str) -> None:
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt = (
        f"---\n"
        f"title: {title}\n"
        f"type: {image_type}\n"
        f"source_skill: baoyu-article-illustrator\n"
        f"language: ko\n"
        f"---\n\n"
        f"# Illustration Prompt\n\n"
        f"- 목적: 매거진 기사 본문 이해를 돕는 시각 보조\n"
        f"- 섹션: {title}\n"
        f"- 타입: {image_type}\n"
        f"- 메모: 실제 생성 백엔드 연결 전까지 placeholder 이미지 사용\n"
    )
    prompt_path.write_text(prompt, encoding="utf-8")


def _create_placeholder(image_path: Path, title: str) -> None:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        image_path.write_bytes(b"")
        return

    img = Image.new("RGB", (1400, 800), color=(246, 240, 231))
    draw = ImageDraw.Draw(img)
    draw.rectangle((60, 60, 1340, 740), outline=(27, 31, 59), width=4)
    draw.text((110, 120), "Claude Magazine Illustration Placeholder", fill=(27, 31, 59))
    draw.text((110, 210), title[:60], fill=(201, 100, 66))
    draw.text((110, 300), "Replace with baoyu-article-illustrator output", fill=(90, 90, 90))
    img.save(image_path, format="PNG")


def _log_illustration(article_id: str, title: str, prompt_path: Path, image_path: Path, skill: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "article_id": article_id,
        "title": title,
        "request_id": f"placeholder-{article_id}",
        "source": skill,
        "model": "local-placeholder",
        "license": "placeholder-for-review",
        "prompt_path": str(prompt_path.relative_to(ROOT)),
        "image_path": str(image_path.relative_to(ROOT)),
    }
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def inject_illustrations(
    markdown: str,
    article_id: str,
    skill: str = "baoyu-article-illustrator",
    relative_to: Path | None = None,
) -> str:
    target_dir = ILLUSTRATION_ROOT / _slugify(article_id, "article")
    prompt_dir = target_dir / "prompts"
    updated = markdown
    targets = _select_targets(markdown)

    for index, (title, image_type) in enumerate(targets, start=1):
        slug = _slugify(title, f"section-{index}")
        image_path = target_dir / f"{index:02d}-{image_type}-{slug}.png"
        prompt_path = prompt_dir / f"{index:02d}-{image_type}-{slug}.md"
        _write_prompt(prompt_path, title, image_type)
        if not image_path.exists():
            _create_placeholder(image_path, title)
        _log_illustration(article_id, title, prompt_path, image_path, skill)

        src = Path("output") / "illustrations" / _slugify(article_id, "article") / image_path.name
        if relative_to is not None:
            try:
                src = Path(os.path.relpath(image_path, relative_to.parent))
            except ValueError:
                src = Path("output") / "illustrations" / _slugify(article_id, "article") / image_path.name

        image_tag = (
            f'<img src="{src.as_posix()}" alt="{title} 시각화" '
            f'data-rights="placeholder-for-review" />'
        )
        heading = f"## {title}"
        replacement = f"{heading}\n\n{image_tag}"
        if heading in updated:
            updated = updated.replace(heading, replacement, 1)
        elif index == 1:
            updated = image_tag + "\n\n" + updated

    return updated
