"""
Inject section illustrations into article drafts.

The hook always returns usable Markdown. Provider failures fall back through a
free-first chain and end at the local placeholder provider.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from pipeline.illustration_providers import (
        IllustrationAuthError,
        IllustrationError,
        IllustrationRateLimitError,
        IllustrationTimeoutError,
    )
    from pipeline.illustration_providers.huggingface import HuggingFaceProvider
    from pipeline.illustration_providers.openai import OpenAIIllustrationProvider
    from pipeline.illustration_providers.placeholder import PlaceholderIllustrationProvider
    from pipeline.illustration_providers.pollinations import PollinationsProvider
except ModuleNotFoundError:
    from illustration_providers import (  # type: ignore
        IllustrationAuthError,
        IllustrationError,
        IllustrationRateLimitError,
        IllustrationTimeoutError,
    )
    from illustration_providers.huggingface import HuggingFaceProvider  # type: ignore
    from illustration_providers.openai import OpenAIIllustrationProvider  # type: ignore
    from illustration_providers.placeholder import PlaceholderIllustrationProvider  # type: ignore
    from illustration_providers.pollinations import PollinationsProvider  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
ILLUSTRATION_ROOT = ROOT / "output" / "illustrations"
LOG_PATH = ROOT / "logs" / "illustrations.jsonl"
DATA_DIR = ROOT / "data"

FALLBACK_CHAIN = {
    "pollinations": ["pollinations", "placeholder"],
    "huggingface": ["huggingface", "pollinations", "placeholder"],
    "openai": ["openai", "placeholder"],
    "placeholder": ["placeholder"],
}


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
        f"- 메모: 단순 장식보다 구조와 정보 전달 우선\n"
    )
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt


def _provider_budget_allows(provider_name: str) -> bool:
    cap = float(os.getenv("CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP", "0.0") or "0.0")
    if cap > 0:
        return True
    return provider_name not in {"openai"}


def _build_provider(provider_name: str):
    if provider_name == "placeholder":
        return PlaceholderIllustrationProvider()
    if provider_name == "pollinations":
        return PollinationsProvider()
    if provider_name == "huggingface":
        return HuggingFaceProvider()
    if provider_name == "openai":
        return OpenAIIllustrationProvider()
    raise IllustrationError(f"Provider '{provider_name}' is not implemented")


def _resolve_provider_chain() -> tuple[list[str], dict[str, Any]]:
    requested = os.getenv("CLAUDE_MAGAZINE_ILLUSTRATION_PROVIDER", "placeholder").strip().lower() or "placeholder"
    chain = list(FALLBACK_CHAIN.get(requested, ["placeholder"]))
    context: dict[str, Any] = {"requested_provider": requested, "provider_chain": chain[:]}
    filtered = [provider for provider in chain if _provider_budget_allows(provider)]
    if not filtered:
        filtered = ["placeholder"]
    if filtered != chain:
        context["budget_filtered"] = True
    return filtered, context


def _cost_state_path(timestamp: datetime) -> Path:
    return DATA_DIR / f"illustration_cost_{timestamp:%Y-%m}.json"


def _update_monthly_cost_state(provider: str, amount: float | None, timestamp: datetime) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _cost_state_path(timestamp)
    payload = {"month": f"{timestamp:%Y-%m}", "total_usd": 0.0, "providers": {}}
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass
    value = float(amount or 0.0)
    payload["total_usd"] = round(float(payload.get("total_usd") or 0.0) + value, 6)
    providers = payload.setdefault("providers", {})
    providers[provider] = round(float(providers.get(provider) or 0.0) + value, 6)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _log_illustration(
    article_id: str,
    title: str,
    prompt_path: Path,
    skill: str,
    result,
    provider_context: dict[str, object],
) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    entry = {
        "timestamp": timestamp.isoformat(),
        "article_id": article_id,
        "title": title,
        "request_id": result.request_id,
        "source": skill,
        "provider": result.provider,
        "provider_chain": provider_context.get("provider_chain", []),
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
    _update_monthly_cost_state(result.provider, result.cost_estimate, timestamp)


def _generate_with_fallback(
    prompt: str,
    size: tuple[int, int],
    article_id: str,
    title: str,
    image_path: Path,
    prompt_path: Path,
    provider_context: dict[str, Any],
):
    chain = list(provider_context.get("provider_chain", []))
    errors: list[dict[str, str]] = []
    placeholder_provider = PlaceholderIllustrationProvider()

    for provider_name in chain:
        try:
            provider = _build_provider(provider_name)
            result = provider.generate(
                prompt,
                size,
                article_id,
                title=title,
                output_path=image_path,
                prompt_path=prompt_path,
            )
            provider_context["selected_provider"] = provider_name
            if errors:
                provider_context["fallback_errors"] = errors
            return result, provider_context
        except IllustrationAuthError as exc:
            errors.append({"provider": provider_name, "type": "auth", "message": str(exc)})
            provider_context["fallback_reason"] = "auth_error"
            break
        except IllustrationRateLimitError as exc:
            errors.append({"provider": provider_name, "type": "rate_limit", "message": str(exc)})
            provider_context["fallback_reason"] = "rate_limit"
            continue
        except IllustrationTimeoutError as exc:
            errors.append({"provider": provider_name, "type": "timeout", "message": str(exc)})
            provider_context["fallback_reason"] = "timeout"
            continue
        except IllustrationError as exc:
            errors.append({"provider": provider_name, "type": "provider_error", "message": str(exc)})
            provider_context["fallback_reason"] = "provider_error"
            continue
        except Exception as exc:
            errors.append({"provider": provider_name, "type": "unexpected", "message": str(exc)})
            provider_context["fallback_reason"] = "unexpected_error"
            continue

    provider_context["selected_provider"] = "placeholder"
    if errors:
        provider_context["fallback_errors"] = errors
    result = placeholder_provider.generate(
        prompt,
        size,
        article_id,
        title=title,
        output_path=image_path,
        prompt_path=prompt_path,
    )
    return result, provider_context


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
    provider_chain, base_context = _resolve_provider_chain()

    for index, (title, image_type) in enumerate(targets, start=1):
        slug = _slugify(title, f"section-{index}")
        image_path = target_dir / f"{index:02d}-{image_type}-{slug}.png"
        prompt_path = prompt_dir / f"{index:02d}-{image_type}-{slug}.md"
        prompt = _write_prompt(prompt_path, title, image_type)
        provider_context = {**base_context, "provider_chain": provider_chain[:], "image_type": image_type}
        result, provider_context = _generate_with_fallback(
            prompt,
            (1400, 800),
            article_id,
            title,
            image_path,
            prompt_path,
            provider_context,
        )
        _log_illustration(article_id, title, prompt_path, skill, result, provider_context)

        src = Path("output") / "illustrations" / _slugify(article_id, "article") / result.image_path.name
        if relative_to is not None:
            try:
                src = Path(os.path.relpath(result.image_path, relative_to.parent))
            except ValueError:
                src = Path("output") / "illustrations" / _slugify(article_id, "article") / result.image_path.name

        image_tag = f'<img src="{src.as_posix()}" alt="{title} 시각화" data-rights="{result.license}" />'
        heading = f"## {title}"
        replacement = f"{heading}\n\n{image_tag}"
        if heading in updated:
            updated = updated.replace(heading, replacement, 1)
        elif index == 1:
            updated = image_tag + "\n\n" + updated

    return updated
