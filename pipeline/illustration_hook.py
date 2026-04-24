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

try:
    from pipeline.illustration_providers.openai import OpenAIIllustrationProvider
    from pipeline.illustration_providers.placeholder import PlaceholderIllustrationProvider
except ModuleNotFoundError:
    from illustration_providers.openai import OpenAIIllustrationProvider  # type: ignore
    from illustration_providers.placeholder import PlaceholderIllustrationProvider  # type: ignore
except Exception:
    from pipeline.illustration_providers.placeholder import PlaceholderIllustrationProvider

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


def _write_prompt(prompt_path: Path, title: str, image_type: str) -> str:
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
    return prompt


def _resolve_provider() -> tuple[object, dict[str, object]]:
    requested = os.getenv("CLAUDE_MAGAZINE_ILLUSTRATION_PROVIDER", "placeholder").strip().lower()
    if requested in {"", "placeholder"}:
        return PlaceholderIllustrationProvider(), {"requested_provider": "placeholder"}
    if requested == "openai":
        return OpenAIIllustrationProvider(), {"requested_provider": "openai"}
    return PlaceholderIllustrationProvider(), {
        "requested_provider": requested,
        "fallback_reason": "provider_not_implemented",
    }


def _log_illustration(
    article_id: str,
    title: str,
    prompt_path: Path,
    skill: str,
    result,
    provider_context: dict[str, object],
) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "article_id": article_id,
        "title": title,
        "request_id": result.request_id,
        "source": skill,
        "provider": result.provider,
        "model": result.model,
        "license": result.license,
        "cost_estimate": result.cost_estimate,
        "prompt_path": str(prompt_path.relative_to(ROOT)),
        "image_path": str(result.image_path.relative_to(ROOT)),
        "provider_context": provider_context,
        "metadata": result.metadata,
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
    provider, provider_context = _resolve_provider()
    placeholder_provider = PlaceholderIllustrationProvider()

    for index, (title, image_type) in enumerate(targets, start=1):
        slug = _slugify(title, f"section-{index}")
        image_path = target_dir / f"{index:02d}-{image_type}-{slug}.png"
        prompt_path = prompt_dir / f"{index:02d}-{image_type}-{slug}.md"
        prompt = _write_prompt(prompt_path, title, image_type)
        try:
            result = provider.generate(
                prompt,
                (1400, 800),
                article_id,
                title=title,
                output_path=image_path,
                prompt_path=prompt_path,
            )
        except Exception as exc:
            provider_context = {
                **provider_context,
                "fallback_reason": "provider_error",
                "fallback_error": str(exc),
            }
            result = placeholder_provider.generate(
                prompt,
                (1400, 800),
                article_id,
                title=title,
                output_path=image_path,
                prompt_path=prompt_path,
            )
        _log_illustration(article_id, title, prompt_path, skill, result, provider_context)

        src = Path("output") / "illustrations" / _slugify(article_id, "article") / result.image_path.name
        if relative_to is not None:
            try:
                src = Path(os.path.relpath(result.image_path, relative_to.parent))
            except ValueError:
                src = Path("output") / "illustrations" / _slugify(article_id, "article") / result.image_path.name

        image_tag = (
            f'<img src="{src.as_posix()}" alt="{title} 시각화" '
            f'data-rights="{result.license}" />'
        )
        heading = f"## {title}"
        replacement = f"{heading}\n\n{image_tag}"
        if heading in updated:
            updated = updated.replace(heading, replacement, 1)
        elif index == 1:
            updated = image_tag + "\n\n" + updated

    return updated
