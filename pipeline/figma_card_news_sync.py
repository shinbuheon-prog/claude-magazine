from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from pipeline.figma_client import FigmaClient, ensure_free_plan_compatible
except ModuleNotFoundError:
    from figma_client import FigmaClient, ensure_free_plan_compatible  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "logs" / "card_news.jsonl"
OUTPUT_DIR = ROOT / "output" / "figma_sync"

FRAME_SIZE = {"width": 1080, "height": 1350}
SUPPORTED_LAYOUTS = {"layout_1", "layout_4", "layout_6"}
LAYOUT_FALLBACKS = {
    "layout_2": "layout_1",
    "layout_3": "layout_1",
    "layout_5": "layout_4",
    "layout_7": "layout_6",
}
LAYOUT_SLOTS = {
    "layout_1": {
        "tag": {"x": 72, "y": 72, "width": 220, "height": 56},
        "main_copy": {"x": 72, "y": 180, "width": 936, "height": 300},
        "sub_copy": {"x": 72, "y": 520, "width": 780, "height": 220},
        "highlight": {"x": 792, "y": 520, "width": 216, "height": 220},
        "footer": {"x": 72, "y": 1238, "width": 936, "height": 48},
    },
    "layout_4": {
        "tag": {"x": 360, "y": 88, "width": 360, "height": 56},
        "main_copy": {"x": 120, "y": 280, "width": 840, "height": 340},
        "sub_copy": {"x": 160, "y": 700, "width": 760, "height": 180},
        "highlight": {"x": 120, "y": 980, "width": 840, "height": 120},
        "footer": {"x": 72, "y": 1238, "width": 936, "height": 48},
    },
    "layout_6": {
        "tag": {"x": 72, "y": 72, "width": 220, "height": 56},
        "highlight": {"x": 760, "y": 92, "width": 248, "height": 80},
        "main_copy": {"x": 72, "y": 260, "width": 936, "height": 380},
        "sub_copy": {"x": 72, "y": 720, "width": 860, "height": 220},
        "footer": {"x": 72, "y": 1238, "width": 936, "height": 48},
    },
}


def _resolve_layout(layout: str) -> tuple[str, str | None]:
    if layout in SUPPORTED_LAYOUTS:
        return layout, None
    fallback = LAYOUT_FALLBACKS.get(layout, "layout_1")
    return fallback, layout


def _build_frame(slide: dict[str, object]) -> dict[str, object]:
    requested_layout = str(slide.get("layout") or "layout_1")
    resolved_layout, fallback_from = _resolve_layout(requested_layout)
    slots = LAYOUT_SLOTS[resolved_layout]
    idx = int(slide.get("idx") or 0)
    children = []
    for slot_name in ("tag", "main_copy", "sub_copy", "highlight", "footer"):
        bounds = slots[slot_name]
        children.append(
            {
                "node_id": f"planned:{idx}:{slot_name}",
                "name": slot_name,
                "type": "TEXT" if slot_name != "tag" else "GROUP",
                "bounds": bounds,
                "text": slide.get(slot_name, ""),
            }
        )
    return {
        "node_id": f"planned:{idx}",
        "name": f"Slide/{idx:02d}",
        "slide_idx": idx,
        "role": slide.get("role"),
        "requested_layout": requested_layout,
        "resolved_layout": resolved_layout,
        "fallback_from": fallback_from,
        "frame": FRAME_SIZE,
        "children": children,
    }


def build_sync_plan(payload: dict[str, object], file_key: str) -> dict[str, object]:
    slides = payload.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("slides-json must contain a non-empty slides array")
    frames = [_build_frame(slide) for slide in slides if isinstance(slide, dict)]
    if not frames or slides[0].get("role") != "hook" or slides[-1].get("role") != "cta":
        raise ValueError("card-news slide schema invalid: hook/cta missing")
    return {
        "provider": "figma-rest-free",
        "sync_status": "planned",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel": payload.get("channel"),
        "format": payload.get("format"),
        "file_key": file_key,
        "file_url": f"https://www.figma.com/design/{file_key}",
        "frames": frames,
        "meta": payload.get("meta", {}),
    }


def generate_paste_package(payload: dict[str, Any], plan: dict[str, Any], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    slides = payload.get("slides") or []
    for frame, slide in zip(plan.get("frames", []), slides):
        if not isinstance(frame, dict) or not isinstance(slide, dict):
            continue
        idx = int(slide.get("idx") or 0)
        role = str(slide.get("role") or "body")
        path = output_dir / f"slide_{idx:02d}_{role}.md"
        lines = [
            f"# Slide {idx:02d} ({role})",
            "",
            f"- Layout: {frame.get('resolved_layout')}",
            f"- Requested layout: {frame.get('requested_layout')}",
            f"- Figma frame size: {FRAME_SIZE['width']}x{FRAME_SIZE['height']}",
            "",
            "## Paste Order",
            "",
            f"1. Tag: {slide.get('tag', '')}",
            f"2. Main copy: {slide.get('main_copy', '')}",
            f"3. Sub copy: {slide.get('sub_copy', '')}",
            f"4. Highlight: {slide.get('highlight', '')}",
            f"5. Footer: {slide.get('footer', '')}",
            "",
            "## Auto Layout Notes",
            "",
            "- Keep the frame at 1080x1350.",
            "- Paste each text block into the matching layer name.",
            "- Apply local styling after paste; this package only carries copy and layout intent.",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        written.append(str(path))

    index_path = output_dir / "README.md"
    index_lines = [
        "# Figma Paste Package",
        "",
        f"- File key: {plan.get('file_key')}",
        f"- File URL: {plan.get('file_url')}",
        f"- Slides: {len(written)}",
        "",
        "Use the per-slide Markdown files to paste copy into a prepared Figma template.",
    ]
    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    written.append(str(index_path))
    return written


def _append_log(plan: dict[str, object], slides_json: Path, extra: dict[str, object] | None = None) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": None,
        "channel": plan.get("channel"),
        "format": plan.get("format"),
        "total_slides": len(plan.get("frames", [])),
        "figma_provider": plan.get("provider"),
        "figma_sync_status": plan.get("sync_status"),
        "figma_file_key": plan.get("file_key"),
        "figma_file_url": plan.get("file_url"),
        "figma_node_ids": [frame["node_id"] for frame in plan.get("frames", []) if isinstance(frame, dict)],
        "source_bundle": str(slides_json.relative_to(ROOT)) if slides_json.is_relative_to(ROOT) else str(slides_json),
    }
    if extra:
        entry.update(extra)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _mask_token(token: str | None) -> str | None:
    if not token:
        return None
    return f"{token[:5]}***"


def _resolve_output_path(slides_path: Path, out: str | None) -> Path:
    if out:
        return Path(out)
    return OUTPUT_DIR / f"{slides_path.stem}_figma_plan.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build free-plan Figma sync assets from card-news slide JSON")
    parser.add_argument("--slides-json", required=True, help="TASK_041 card-news JSON path")
    parser.add_argument("--file-key", required=True, help="Target Figma file key")
    parser.add_argument("--access-token", help="Figma personal access token; falls back to FIGMA_ACCESS_TOKEN")
    parser.add_argument("--out", help="Optional output plan JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Build sync assets only")
    parser.add_argument("--paste-package", action="store_true", help="Generate per-slide Markdown files for manual paste")
    parser.add_argument("--paste-package-dir", help="Optional output directory for paste-package assets")
    parser.add_argument("--export-images", help="Comma-separated Figma frame node IDs to export as PNG")
    parser.add_argument("--image-scale", type=int, default=2, help="Figma export scale")
    args = parser.parse_args()

    slides_path = Path(args.slides_json)
    if not slides_path.exists():
        print(f"[FAIL] slides-json not found: {slides_path}", file=sys.stderr)
        return 1

    payload = json.loads(slides_path.read_text(encoding="utf-8-sig"))
    plan = build_sync_plan(payload, args.file_key)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _resolve_output_path(slides_path, args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    paste_files: list[str] = []
    if args.paste_package:
        paste_dir = Path(args.paste_package_dir) if args.paste_package_dir else OUTPUT_DIR / f"{slides_path.stem}_paste"
        paste_files = generate_paste_package(payload, plan, paste_dir)

    metadata: dict[str, Any] | None = None
    profile: dict[str, Any] | None = None
    warnings: list[str] = []
    exported: list[dict[str, Any]] = []

    token = args.access_token or os.getenv("FIGMA_ACCESS_TOKEN", "")
    if token and (args.export_images or not args.dry_run):
        try:
            client = FigmaClient(token)
            profile = client.validate_token()
            metadata = client.get_file_metadata(args.file_key)
            warnings.extend(ensure_free_plan_compatible(metadata, profile))
            if args.export_images:
                frame_ids = [item.strip() for item in args.export_images.split(",") if item.strip()]
                export_dir = OUTPUT_DIR / f"{slides_path.stem}_exports"
                exported = client.export_frame_images(args.file_key, frame_ids, export_dir, scale=args.image_scale)
        except Exception as exc:
            print(f"[FAIL] Figma REST request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
    elif args.export_images:
        print("[FAIL] --export-images requires FIGMA_ACCESS_TOKEN or --access-token", file=sys.stderr)
        return 1

    _append_log(
        plan,
        slides_path,
        {
            "paste_package": bool(args.paste_package),
            "paste_files": [str(Path(path)) for path in paste_files],
            "exported_images": exported,
            "figma_warnings": warnings,
            "token_masked": _mask_token(token),
        },
    )

    result = {
        "plan_path": str(out_path),
        "plan": plan,
        "paste_package_files": paste_files,
        "figma_profile": profile,
        "figma_metadata": metadata,
        "warnings": warnings,
        "exported_images": exported,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
