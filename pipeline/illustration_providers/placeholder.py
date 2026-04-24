from __future__ import annotations

from pathlib import Path

from . import IllustrationProvider, IllustrationResult


class PlaceholderIllustrationProvider(IllustrationProvider):
    name = "placeholder"
    requires_env: tuple[str, ...] = ()

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
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not output_path.exists():
            self._create_placeholder(output_path, title, size=size)
        return IllustrationResult(
            image_path=output_path,
            provider=self.name,
            model="local-placeholder",
            request_id=f"placeholder-{article_id}",
            license="placeholder-for-review",
            cost_estimate=None,
            prompt_path=prompt_path,
            metadata={
                "reason": "no_remote_provider_wired",
                "prompt_preview": prompt[:160],
            },
        )

    @staticmethod
    def _create_placeholder(image_path: Path, title: str, size: tuple[int, int]) -> None:
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            image_path.write_bytes(b"")
            return

        width, height = size
        img = Image.new("RGB", (width, height), color=(246, 240, 231))
        draw = ImageDraw.Draw(img)
        draw.rectangle((60, 60, width - 60, height - 60), outline=(27, 31, 59), width=4)
        draw.text((110, 120), "Claude Magazine Illustration Placeholder", fill=(27, 31, 59))
        draw.text((110, 210), title[:60], fill=(201, 100, 66))
        draw.text((110, 300), "Replace with provider output", fill=(90, 90, 90))
        img.save(image_path, format="PNG")
