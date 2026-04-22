from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.__stdout__ is not None:
    sys.stdout = sys.__stdout__
if sys.__stderr__ is not None:
    sys.stderr = sys.__stderr__

load_dotenv()

DRAFTS_DIR = ROOT / "drafts"
LOGS_DIR = ROOT / "logs"
PUBLISH_ACTIONS_PATH = LOGS_DIR / "publish_actions.jsonl"

DRAFTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}

app = FastAPI(title="Claude Magazine Editor API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApprovePayload(BaseModel):
    approver: str = Field(default="local-editor")
    send_newsletter: bool = False
    disclosure_template: str = Field(default="heavy")
    notes: str = ""


class RejectPayload(BaseModel):
    approver: str = Field(default="local-editor")
    reason: str = ""


def _require_local(request: Request) -> None:
    client_host = request.client.host if request.client else ""
    if client_host not in LOCAL_HOSTS:
        raise HTTPException(status_code=403, detail="Editor API is local-only.")


def _require_token(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("EDITOR_API_TOKEN", "").strip()
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing editor API bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid editor API token.")


def _guard(request: Request, _: None = Depends(_require_token)) -> None:
    _require_local(request)


def _lint_draft(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from pipeline.editorial_lint import lint_draft
    return lint_draft(*args, **kwargs)


def _inject_disclosure(html: str, template: str) -> str:
    from pipeline.disclosure_injector import inject_disclosure
    return inject_disclosure(html, template=template)


def _create_post(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from pipeline.ghost_client import create_post
    return create_post(*args, **kwargs)


def _send_newsletter(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from pipeline.ghost_client import send_newsletter
    return send_newsletter(*args, **kwargs)


def _collect_metrics() -> dict[str, Any]:
    from pipeline.metrics_collector import collect_metrics
    return collect_metrics(since_days=30)


def _check_article_standards(draft_path: str, category: str, article_id: str) -> Any:
    try:
        from pipeline.standards_checker import check_article
    except Exception:
        return None
    try:
        return check_article(draft_path, category.lower(), {"article_id": article_id})
    except Exception:
        return None


def _check_source_diversity(article_id: str) -> Any:
    try:
        from pipeline.source_diversity import check_diversity
    except Exception:
        return None
    try:
        return check_diversity(article_id)
    except Exception:
        return None


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-_") or "untitled"


def _extract_title(markdown_text: str, fallback: str) -> str:
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _markdown_to_html(markdown_text: str) -> str:
    paragraphs = [part.strip() for part in markdown_text.split("\n\n") if part.strip()]
    html_parts: list[str] = []
    for paragraph in paragraphs:
        if paragraph.startswith("# "):
            html_parts.append(f"<h1>{paragraph[2:].strip()}</h1>")
        elif paragraph.startswith("## "):
            html_parts.append(f"<h2>{paragraph[3:].strip()}</h2>")
        else:
            html_parts.append(f"<p>{paragraph.replace(chr(10), '<br/>')}</p>")
    return "\n".join(html_parts)


def _has_ghost_env() -> bool:
    return bool(os.getenv("GHOST_ADMIN_API_URL") and os.getenv("GHOST_ADMIN_API_KEY"))


def _all_publish_logs() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(LOGS_DIR.glob("publish_*.json"), reverse=True):
        data = _read_json(path, {})
        if not isinstance(data, dict):
            continue
        data["log_file"] = path.name
        entries.append(data)
    return entries


def _read_publish_actions() -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not PUBLISH_ACTIONS_PATH.exists():
        return actions
    for line in PUBLISH_ACTIONS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            actions.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return actions


def _append_publish_action(entry: dict[str, Any]) -> None:
    with PUBLISH_ACTIONS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _build_brief_text(brief: dict[str, Any]) -> str:
    lines = [
        f"working_title: {brief.get('working_title', '')}",
        f"angle: {brief.get('angle', '')}",
        f"why_now: {brief.get('why_now', '')}",
        "outline:",
    ]
    for section in brief.get("outline", []):
        lines.append(f"- {section.get('section', '')}")
        for point in section.get("points", []):
            lines.append(f"  * {point}")
    return "\n".join(lines)


def _find_draft_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for draft_path in sorted(DRAFTS_DIR.glob("draft_*.md"), reverse=True):
        article_id = draft_path.stem.replace("draft_", "", 1)
        brief_path = DRAFTS_DIR / f"brief_{article_id}.json"
        markdown = draft_path.read_text(encoding="utf-8-sig")
        brief = _read_json(brief_path, {}) if brief_path.exists() else {}
        lint = _lint_draft(str(draft_path), article_id=article_id)
        source_count = len(brief.get("evidence_map", [])) if isinstance(brief, dict) else 0
        word_count = len(markdown.split())
        matching_publish = next(
            (log for log in _all_publish_logs() if log.get("log_file") == f"publish_{article_id}.json"),
            None,
        )
        records.append(
            {
                "article_id": article_id,
                "title": _extract_title(markdown, brief.get("working_title", article_id)),
                "category": brief.get("category", "DRAFT"),
                "updated_at": datetime.fromtimestamp(draft_path.stat().st_mtime).isoformat(),
                "draft_path": str(draft_path.relative_to(ROOT)),
                "brief_path": str(brief_path.relative_to(ROOT)) if brief_path.exists() else None,
                "word_count": word_count,
                "source_count": source_count,
                "lint": {
                    "passed": lint["passed"],
                    "failed": lint["failed"],
                    "warnings": lint["warnings"],
                    "can_publish": lint["can_publish"],
                    "score": max(0, len(lint["items"]) - lint["failed"]),
                    "total": len(lint["items"]),
                },
                "status": matching_publish.get("status", "draft") if matching_publish else "draft",
                "ghost_post_id": matching_publish.get("ghost_post_id", "") if matching_publish else "",
            }
        )
    return records


def _get_record_or_404(article_id: str) -> dict[str, Any]:
    for record in _find_draft_records():
        if record["article_id"] == article_id:
            return record
    raise HTTPException(status_code=404, detail=f"Draft '{article_id}' not found.")


def _publish_log_path(article_id: str) -> Path:
    return LOGS_DIR / f"publish_{article_id}.json"


def _write_publish_log(article_id: str, topic: str, result: dict[str, Any], mode: str) -> dict[str, Any]:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "ghost_post_id": result.get("post_id", ""),
        "ghost_url": result.get("url", ""),
        "mode": mode,
        "status": result.get("status", ""),
        "newsletter_id": result.get("newsletter_id", ""),
        "recipient_count": int(result.get("recipient_count", 0) or 0),
    }
    path = _publish_log_path(article_id)
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    entry["log_file"] = path.name
    return entry


def _approve_draft(record: dict[str, Any], payload: ApprovePayload) -> dict[str, Any]:
    draft_path = ROOT / record["draft_path"]
    brief_path = ROOT / record["brief_path"] if record["brief_path"] else None
    markdown = draft_path.read_text(encoding="utf-8-sig")
    brief = _read_json(brief_path, {}) if brief_path and brief_path.exists() else {}
    lint_result = _lint_draft(str(draft_path), article_id=record["article_id"])
    if not lint_result["can_publish"]:
        raise HTTPException(status_code=400, detail={"message": "Lint failed", "lint": lint_result})

    html = _markdown_to_html(markdown)
    html = _inject_disclosure(html, template=payload.disclosure_template)
    title = _extract_title(markdown, brief.get("working_title", record["title"]))

    if _has_ghost_env():
        result = _create_post(title, html, status="published")
        result["newsletter_id"] = ""
        result["recipient_count"] = 0
        if payload.send_newsletter:
            result.update(_send_newsletter(result["post_id"]))
        result["mode"] = "ghost-live"
    else:
        result = {
            "post_id": f"mock-{record['article_id']}",
            "url": f"http://127.0.0.1/mock/ghost/{_safe_slug(title)}",
            "status": "published",
            "newsletter_id": "mock-newsletter" if payload.send_newsletter else "",
            "recipient_count": 1 if payload.send_newsletter else 0,
            "mode": "mock-ghost",
        }

    publish_log = _write_publish_log(record["article_id"], title, result, result["mode"])
    action = {
        "timestamp": datetime.now().isoformat(),
        "action": "approve",
        "article_id": record["article_id"],
        "approver": payload.approver,
        "send_newsletter": payload.send_newsletter,
        "ghost_post_id": result["post_id"],
        "status": result["status"],
        "notes": payload.notes,
    }
    _append_publish_action(action)
    return {"result": result, "lint": lint_result, "publish_log": publish_log, "action": action}


def _reject_draft(record: dict[str, Any], payload: RejectPayload) -> dict[str, Any]:
    action = {
        "timestamp": datetime.now().isoformat(),
        "action": "reject",
        "article_id": record["article_id"],
        "approver": payload.approver,
        "reason": payload.reason,
    }
    _append_publish_action(action)
    return {"status": "rejected", "action": action}


def _unpublish_live(post_id: str) -> dict[str, Any]:
    from pipeline.ghost_client import _request
    response = _request("GET", f"/posts/{post_id}/")
    post = response["posts"][0]
    payload = {"posts": [{"updated_at": post["updated_at"], "status": "draft"}]}
    updated = _request("PUT", f"/posts/{post_id}/", payload=payload)
    item = updated["posts"][0]
    return {"post_id": item["id"], "status": item["status"], "url": item.get("url", "")}


@app.get("/api/drafts", dependencies=[Depends(_guard)])
def list_drafts() -> dict[str, Any]:
    drafts = _find_draft_records()
    return {"items": drafts, "count": len(drafts)}


@app.get("/api/drafts/{article_id}", dependencies=[Depends(_guard)])
def get_draft(article_id: str) -> dict[str, Any]:
    record = _get_record_or_404(article_id)
    draft_text = (ROOT / record["draft_path"]).read_text(encoding="utf-8-sig")
    brief = _read_json(ROOT / record["brief_path"], {}) if record["brief_path"] else {}
    publish_log = _read_json(_publish_log_path(article_id), None)
    standards = _check_article_standards(str(ROOT / record["draft_path"]), str(record.get("category", "brief")), article_id)
    diversity = _check_source_diversity(article_id)
    return {
        "draft": record,
        "markdown": draft_text,
        "brief": brief,
        "publish_log": publish_log,
        "standards": standards,
        "diversity": diversity,
    }


@app.get("/api/drafts/{article_id}/lint", dependencies=[Depends(_guard)])
def get_draft_lint(article_id: str) -> dict[str, Any]:
    record = _get_record_or_404(article_id)
    return _lint_draft(str(ROOT / record["draft_path"]), article_id=article_id)


@app.get("/api/drafts/{article_id}/diff", dependencies=[Depends(_guard)])
def get_draft_diff(article_id: str) -> dict[str, Any]:
    record = _get_record_or_404(article_id)
    draft_text = (ROOT / record["draft_path"]).read_text(encoding="utf-8-sig")
    brief = _read_json(ROOT / record["brief_path"], {}) if record["brief_path"] else {}
    brief_text = _build_brief_text(brief)
    diff_lines = list(difflib.unified_diff(
        brief_text.splitlines(),
        draft_text.splitlines(),
        fromfile="brief",
        tofile="draft",
        lineterm="",
    ))
    return {"article_id": article_id, "diff": diff_lines}


@app.post("/api/drafts/{article_id}/approve", dependencies=[Depends(_guard)])
def approve_draft(article_id: str, payload: ApprovePayload) -> dict[str, Any]:
    record = _get_record_or_404(article_id)
    return _approve_draft(record, payload)


@app.post("/api/drafts/{article_id}/reject", dependencies=[Depends(_guard)])
def reject_draft(article_id: str, payload: RejectPayload) -> dict[str, Any]:
    record = _get_record_or_404(article_id)
    return _reject_draft(record, payload)


@app.get("/api/published", dependencies=[Depends(_guard)])
def list_published() -> dict[str, Any]:
    items = _all_publish_logs()
    actions = _read_publish_actions()
    unpublish_index = {action.get("ghost_post_id"): action for action in actions if action.get("action") == "unpublish"}
    published_items = []
    for item in items:
        post_id = item.get("ghost_post_id")
        status = "draft" if post_id in unpublish_index else item.get("status", "")
        published_items.append({
            **item,
            "status": status,
            "article_id": item.get("log_file", "").replace("publish_", "").replace(".json", ""),
        })
    return {"items": published_items, "count": len(published_items), "actions": actions}


@app.post("/api/published/{post_id}/unpublish", dependencies=[Depends(_guard)])
def unpublish(post_id: str) -> dict[str, Any]:
    if _has_ghost_env():
        result = _unpublish_live(post_id)
        mode = "ghost-live"
    else:
        result = {"post_id": post_id, "status": "draft", "url": ""}
        mode = "mock-ghost"
    action = {
        "timestamp": datetime.now().isoformat(),
        "action": "unpublish",
        "ghost_post_id": post_id,
        "status": result["status"],
        "mode": mode,
    }
    _append_publish_action(action)
    return {"result": result, "action": action}


@app.get("/api/metrics", dependencies=[Depends(_guard)])
def get_metrics() -> dict[str, Any]:
    return _collect_metrics()


def main() -> int:
    parser = argparse.ArgumentParser(description="Local editor API server")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
