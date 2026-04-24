from __future__ import annotations

import base64
import os
from pathlib import Path

import requests

from . import (
    IllustrationAuthError,
    IllustrationProvider,
    IllustrationRateLimitError,
    IllustrationResult,
    IllustrationTimeoutError,
)

OPENAI_IMAGE_ENDPOINT = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = "gpt-image-1"

_COST_TABLE: dict[tuple[str, str], float] = {
    ("low", "1024x1024"): 0.011,
    ("low", "1024x1536"): 0.016,
    ("low", "1536x1024"): 0.016,
    ("medium", "1024x1024"): 0.042,
    ("medium", "1024x1536"): 0.063,
    ("medium", "1536x1024"): 0.063,
    ("high", "1024x1024"): 0.167,
    ("high", "1024x1536"): 0.25,
    ("high", "1536x1024"): 0.25,
}


def _normalize_size(size: tuple[int, int]) -> str:
    width, height = size
    if abs(width - height) <= min(width, height) * 0.1:
        return "1024x1024"
    if width > height:
        return "1536x1024"
    return "1024x1536"


class OpenAIIllustrationProvider(IllustrationProvider):
    name = "openai"
    requires_env: tuple[str, ...] = ("OPENAI_API_KEY",)

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise IllustrationAuthError("OPENAI_API_KEY is required for the openai illustration provider")
        self.api_key = api_key
        self.model = os.getenv("OPENAI_IMAGE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        self.quality = os.getenv("OPENAI_IMAGE_QUALITY", "low").strip().lower() or "low"
        self.moderation = os.getenv("OPENAI_IMAGE_MODERATION", "auto").strip().lower() or "auto"
        self.timeout_s = int(os.getenv("OPENAI_IMAGE_TIMEOUT_S", "180") or "180")

    def generate(
        self,
        prompt: str,
        size: tuple[int, int],
        article_id: str,
        *,
        title: str,
        output_path: Path,
        prompt_path: Path | None = None,
    ) -> IllustrationResult:
        requested_size = _normalize_size(size)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": requested_size,
            "quality": self.quality,
            "moderation": self.moderation,
        }
        try:
            response = requests.post(
                OPENAI_IMAGE_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_s,
            )
        except requests.Timeout as exc:
            raise IllustrationTimeoutError("OpenAI image request timed out") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"OpenAI image request failed: {exc}") from exc

        if response.status_code in {401, 403}:
            raise IllustrationAuthError("OpenAI image request was not authorized")
        if response.status_code == 429:
            raise IllustrationRateLimitError("OpenAI image request hit a rate limit")
        response.raise_for_status()
        body = response.json()
        data = body.get("data") or []
        if not data or not data[0].get("b64_json"):
            raise RuntimeError("OpenAI image response did not include data[0].b64_json")

        image_bytes = base64.b64decode(data[0]["b64_json"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)

        return IllustrationResult(
            image_path=output_path,
            provider=self.name,
            model=self.model,
            request_id=response.headers.get("x-request-id") or f"openai-{article_id}",
            license="openai-api-output",
            cost_estimate=_COST_TABLE.get((self.quality, requested_size)),
            prompt_path=prompt_path,
            metadata={
                "title": title,
                "requested_size": requested_size,
                "quality": self.quality,
                "moderation": self.moderation,
                "revised_prompt": data[0].get("revised_prompt"),
            },
        )
