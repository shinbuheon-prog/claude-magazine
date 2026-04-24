from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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
        children.append({
            "node_id": f"planned:{idx}:{slot_name}",
            "name": slot_name,
            "type": "TEXT" if slot_name != "tag" else "GROUP",
            "bounds": bounds,
            "text": slide.get(slot_name, ""),
        })
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
        "provider": "official-mcp-remote",
        "sync_status": "planned",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel": payload.get("channel"),
        "format": payload.get("format"),
        "file_key": file_key,
        "file_url": f"https://www.figma.com/design/{file_key}",
        "frames": frames,
        "meta": payload.get("meta", {}),
    }


def _append_log(plan: dict[str, object], slides_json: Path) -> None:
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
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Figma sync plan from card-news slide JSON")
    parser.add_argument("--slides-json", required=True, help="TASK_041 card-news JSON path")
    parser.add_argument("--file-key", required=True, help="Target Figma file key")
    parser.add_argument("--out", help="Optional output plan JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Build a sync plan only; do not attempt live sync")
    args = parser.parse_args()

    slides_path = Path(args.slides_json)
    if not slides_path.exists():
        print(f"[FAIL] slides-json not found: {slides_path}", file=sys.stderr)
        return 1

    payload = json.loads(slides_path.read_text(encoding="utf-8"))
    plan = build_sync_plan(payload, args.file_key)

    if not args.dry_run:
        print("[FAIL] live Figma MCP execution is not available in this local CLI yet; use --dry-run", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else OUTPUT_DIR / f"{slides_path.stem}_figma_plan.json"
    out_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    _append_log(plan, slides_path)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
