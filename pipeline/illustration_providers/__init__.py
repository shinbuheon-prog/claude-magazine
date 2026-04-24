from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class IllustrationResult:
    image_path: Path
    provider: str
    model: str
    request_id: str
    license: str
    cost_estimate: float | None = None
    prompt_path: Path | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class IllustrationProvider(ABC):
    name = "base"
    requires_env: tuple[str, ...] = ()

    @abstractmethod
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
        raise NotImplementedError
