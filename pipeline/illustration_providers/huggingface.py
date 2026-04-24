from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from . import (
    IllustrationAuthError,
    IllustrationProvider,
    IllustrationRateLimitError,
    IllustrationResult,
    IllustrationTimeoutError,
)

SAFE_LICENSES = {
    "black-forest-labs/FLUX.1-schnell": "Apache-2.0",
    "stabilityai/stable-diffusion-xl-base-1.0": "CreativeML Open RAIL-M",
}


class HuggingFaceProvider(IllustrationProvider):
    name = "huggingface"
    requires_env: tuple[str, ...] = ("HUGGINGFACE_TOKEN",)
    DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"

    def __init__(self, timeout_s: int = 120) -> None:
        token = os.getenv("HUGGINGFACE_TOKEN", "").strip()
        if not token:
            raise IllustrationAuthError("HUGGINGFACE_TOKEN is required for the huggingface illustration provider")
        self.token = token
        self.timeout_s = timeout_s
        self.model = os.getenv("HUGGINGFACE_IMAGE_MODEL", self.DEFAULT_MODEL).strip() or self.DEFAULT_MODEL
        if self.model not in SAFE_LICENSES:
            raise IllustrationAuthError(f"HuggingFace model '{self.model}' is not in the safe-license allowlist")

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
        width, height = size
        endpoint = f"https://api-inference.huggingface.co/models/{self.model}"
        payload = {"inputs": prompt, "parameters": {"width": width, "height": height}}
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                response = requests.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                        "User-Agent": "Claude-Magazine-KR/1.0",
                    },
                    json=payload,
                    timeout=self.timeout_s,
                )
            except requests.Timeout as exc:
                last_error = IllustrationTimeoutError("HuggingFace image request timed out")
            except requests.RequestException as exc:
                last_error = exc
            else:
                if response.status_code in {401, 403}:
                    raise IllustrationAuthError("HuggingFace image request was not authorized")
                if response.status_code == 429:
                    last_error = IllustrationRateLimitError("HuggingFace image request hit a rate limit")
                elif response.status_code == 503:
                    last_error = IllustrationRateLimitError("HuggingFace model is still loading")
                else:
                    response.raise_for_status()
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(response.content)
                    return IllustrationResult(
                        image_path=output_path,
                        provider=self.name,
                        model=self.model,
                        request_id=response.headers.get("x-request-id") or f"huggingface-{article_id}",
                        license=SAFE_LICENSES[self.model],
                        cost_estimate=0.0,
                        prompt_path=prompt_path,
                        metadata={"title": title, "width": width, "height": height},
                    )
            if attempt < 2:
                time.sleep(2 * (attempt + 1))

        if isinstance(last_error, IllustrationRateLimitError):
            raise last_error
        if isinstance(last_error, IllustrationTimeoutError):
            raise last_error
        raise RuntimeError(f"HuggingFace image request failed: {last_error}")
