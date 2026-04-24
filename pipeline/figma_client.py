from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests

FIGMA_API_BASE = "https://api.figma.com/v1"


class FigmaClient:
    """Minimal Figma REST wrapper for free-plan compatible read/export flows."""

    def __init__(self, access_token: str | None = None, timeout_s: int = 60) -> None:
        token = (access_token or os.getenv("FIGMA_ACCESS_TOKEN", "")).strip()
        if not token:
            raise RuntimeError("FIGMA_ACCESS_TOKEN is required")
        self.access_token = token
        self.timeout_s = timeout_s

    def _headers(self) -> dict[str, str]:
        return {
            "X-Figma-Token": self.access_token,
            "User-Agent": "Claude-Magazine-KR/1.0",
        }

    def _get(self, path: str, **params: object) -> dict[str, Any]:
        response = requests.get(
            f"{FIGMA_API_BASE}{path}",
            headers=self._headers(),
            params={key: value for key, value in params.items() if value not in (None, "")},
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        return response.json()

    def validate_token(self) -> dict[str, Any]:
        profile = self._get("/me")
        return {
            "email": profile.get("email"),
            "handle": profile.get("handle"),
            "id": profile.get("id"),
            "img_url": profile.get("img_url"),
        }

    def get_file_metadata(self, file_key: str) -> dict[str, Any]:
        payload = self._get(f"/files/{file_key}")
        document = payload.get("document") or {}
        return {
            "name": payload.get("name"),
            "last_modified": payload.get("lastModified"),
            "version": payload.get("version"),
            "role": payload.get("role"),
            "editor_type": payload.get("editorType"),
            "document_name": document.get("name"),
            "document_id": document.get("id"),
            "components_count": len(payload.get("components") or {}),
            "schema_version": payload.get("schemaVersion"),
        }

    def export_frame_images(
        self,
        file_key: str,
        frame_node_ids: list[str],
        output_dir: Path,
        *,
        scale: int = 2,
        image_format: str = "png",
    ) -> list[dict[str, Any]]:
        if not frame_node_ids:
            return []

        payload = self._get(
            f"/images/{file_key}",
            ids=",".join(frame_node_ids),
            format=image_format,
            scale=scale,
        )
        images = payload.get("images") or {}
        output_dir.mkdir(parents=True, exist_ok=True)

        exported: list[dict[str, Any]] = []
        for node_id in frame_node_ids:
            image_url = images.get(node_id)
            if not image_url:
                exported.append({"node_id": node_id, "status": "missing"})
                continue
            response = requests.get(
                image_url,
                headers=self._headers(),
                timeout=self.timeout_s,
            )
            response.raise_for_status()
            safe_name = node_id.replace(":", "_")
            image_path = output_dir / f"{safe_name}.{image_format}"
            image_path.write_bytes(response.content)
            exported.append(
                {
                    "node_id": node_id,
                    "status": "exported",
                    "image_path": str(image_path),
                    "image_url": image_url,
                }
            )
        return exported


def ensure_free_plan_compatible(metadata: dict[str, Any], profile: dict[str, Any] | None = None) -> list[str]:
    warnings: list[str] = []
    role = str(metadata.get("role") or "").lower()
    if role and role not in {"owner", "editor"}:
        warnings.append(f"Figma role is '{role}', so manual paste/export may be read-only.")

    document_name = str(metadata.get("document_name") or metadata.get("name") or "")
    if document_name and "team" in document_name.lower():
        warnings.append("File name suggests a shared workspace. Personal drafts are recommended for the free-plan path.")

    email = str((profile or {}).get("email") or "")
    if email and email.count("@") == 1 and not email.endswith(("@gmail.com", "@outlook.com", "@hotmail.com", "@naver.com")):
        warnings.append("Token email looks like a workspace account. Verify that the target file is a personal draft.")

    return warnings
