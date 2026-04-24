from __future__ import annotations

import time
import urllib.parse
from pathlib import Path

import requests

from . import (
    IllustrationProvider,
    IllustrationRateLimitError,
    IllustrationResult,
    IllustrationTimeoutError,
)

POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt"


class PollinationsProvider(IllustrationProvider):
    name = "pollinations"
    requires_env: tuple[str, ...] = ()

    def __init__(self, timeout_s: int = 60) -> None:
        self.timeout_s = timeout_s

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
        encoded_prompt = urllib.parse.quote(prompt, safe="")
        url = f"{POLLINATIONS_BASE_URL}/{encoded_prompt}"
        params = {
            "width": width,
            "height": height,
            "model": "flux",
            "nologo": "true",
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers={"User-Agent": "Claude-Magazine-KR/1.0"},
                    timeout=self.timeout_s,
                )
            except requests.Timeout:
                last_error = IllustrationTimeoutError("Pollinations request timed out")
            except requests.RequestException as exc:
                last_error = exc
            else:
                if response.status_code == 429:
                    last_error = IllustrationRateLimitError("Pollinations rate limit")
                else:
                    response.raise_for_status()
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(response.content)
                    return IllustrationResult(
                        image_path=output_path,
                        provider=self.name,
                        model="flux",
                        request_id=f"pollinations-{article_id}",
                        license="pollinations-free-tier",
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
        raise RuntimeError(f"Pollinations request failed: {last_error}")
