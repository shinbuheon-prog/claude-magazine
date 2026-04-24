"""
소스 자동 수집 파이프라인 (TASK_032)

RSS/Atom 피드를 수집해 source_registry에 자동 등록.
WorldMonitor "500+ feeds → AI briefs" 패턴 차용.

사용법:
    from pipeline.source_ingester import ingest_feeds
    result = ingest_feeds(feeds_path="config/feeds.yml", dry_run=False)
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Windows UTF-8 강제 (중복 적용 가드)
if sys.platform == "win32" and not getattr(sys.stdout, "_cm_utf8", False):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdout._cm_utf8 = True  # type: ignore[attr-defined]
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

try:
    import feedparser  # type: ignore
except ImportError:
    feedparser = None  # lazy — 실행 시 체크

try:
    import yaml  # PyYAML
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "data" / "source_ingest_state.json"
DEFAULT_FEEDS = ROOT / "config" / "feeds.yml"
INGESTED_DIR = ROOT / "drafts" / "ingested"
NETWORK_TIMEOUT = 15
CONTENT_PREVIEW_MAX = 150


# ── 유틸 ──────────────────────────────────────────

def _load_feeds(feeds_path: str | Path) -> list[dict[str, Any]]:
    """feeds.yml 로드. enabled=false는 제외."""
    if yaml is None:
        raise RuntimeError("PyYAML 미설치 — requirements.txt 설치 필요")

    path = Path(feeds_path) if not Path(feeds_path).is_absolute() else Path(feeds_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"feeds 설정 파일 없음: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    feeds = data.get("feeds", [])
    normalized = []
    for item in feeds:
        if not item.get("enabled", True):
            continue
        row = dict(item)
        row["type"] = str(row.get("type", "rss")).lower()
        normalized.append(row)
    return normalized


def _load_state() -> dict[str, str]:
    """마지막 수집 timestamp 맵 로드. 없으면 빈 dict."""
    if not STATE_PATH.exists():
        return {}
    try:
        with STATE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # state 파일 손상 시 전체 재수집으로 fallback
        return {}


def _save_state(state: dict[str, str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _parse_published(entry: Any) -> datetime | None:
    """feedparser entry에서 published datetime 추출. 실패 시 None."""
    for key in ("published_parsed", "updated_parsed"):
        tup = getattr(entry, key, None) or (entry.get(key) if hasattr(entry, "get") else None)
        if tup:
            try:
                return datetime(*tup[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _entry_preview(entry: Any, max_chars: int = CONTENT_PREVIEW_MAX) -> str:
    """entry의 summary 또는 title을 preview로 축약."""
    summary = ""
    if hasattr(entry, "summary"):
        summary = entry.summary or ""
    elif hasattr(entry, "get"):
        summary = entry.get("summary", "") or entry.get("description", "") or ""

    if not summary:
        summary = getattr(entry, "title", "") or ""

    # HTML 태그 간이 제거
    import re
    clean = re.sub(r"<[^>]+>", " ", summary)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:max_chars]


def _slugify(value: str, fallback: str = "item") -> str:
    text = re.sub(r"[^\w\s-]", " ", value, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "-", text).strip("-").lower()
    return text[:80] or fallback


def _fetch_text_content(url: str) -> tuple[str, str]:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("requests/beautifulsoup4 미설치 — URL 수집 불가") from exc

    response = requests.get(url, timeout=NETWORK_TIMEOUT, headers={"User-Agent": "claude-magazine/1.0"})
    response.raise_for_status()
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string if soup.title and soup.title.string else "").strip()
    paras = []
    for tag in soup.find_all(["p", "li"]):
        text = " ".join(tag.get_text(" ", strip=True).split())
        if text:
            paras.append(text)
        if len(paras) >= 8:
            break
    body = "\n\n".join(paras)
    if not body:
        body = "본문 추출 실패 — 외부 스킬 또는 수동 검토 필요"
    return title or url, body


def _write_ingested_markdown(kind: str, slug: str, title: str, source_url: str, body: str) -> Path:
    target_dir = INGESTED_DIR / kind
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{slug}.md"
    content = (
        f"# {title}\n\n"
        f"- kind: {kind}\n"
        f"- source_url: {source_url}\n"
        f"- ingested_at: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"{body}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def _extract_youtube_video_id(url: str) -> str | None:
    patterns = [
        r"v=([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"/embed/([A-Za-z0-9_-]{11})",
        r"/shorts/([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def ingest_url(feed_config: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    source_url = str(feed_config.get("url", "")).strip()
    if not source_url:
        raise ValueError("url type feed에 url 필수")

    name = str(feed_config.get("name") or source_url)
    if dry_run:
        title = name
        body = "dry-run URL 수집 미리보기 — 실제 HTML fetch 생략"
    else:
        title, body = _fetch_text_content(source_url)

    slug = _slugify(title, fallback="url-source")
    artifact_path = None if dry_run else _write_ingested_markdown("url", slug, title, source_url, body)
    return {
        "title": title,
        "preview": body[:CONTENT_PREVIEW_MAX],
        "artifact_path": str(artifact_path.relative_to(ROOT)) if artifact_path else "",
        "entry_url": source_url,
        "publisher": name,
        "topics": list(feed_config.get("topics", [])),
        "classified_by": "baoyu-url-to-markdown-wrapper",
    }


def ingest_youtube(feed_config: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    source_url = str(feed_config.get("url", "")).strip()
    if not source_url:
        raise ValueError("youtube type feed에 url 필수")

    video_id = _extract_youtube_video_id(source_url)
    if not video_id:
        raise ValueError(f"YouTube video id 추출 실패: {source_url}")

    title = str(feed_config.get("name") or f"YouTube {video_id}")
    cover_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    body_lines = [
        "## Transcript",
        "실제 자막 추출은 baoyu-youtube-transcript 런타임 또는 후속 수동 실행이 필요합니다.",
        "",
        "## Metadata",
        f"- video_id: {video_id}",
        f"- cover_image: {cover_url}",
        f"- source_url: {source_url}",
    ]
    if dry_run:
        body_lines.insert(1, "dry-run: 네트워크 호출 없이 메타데이터만 검증")

    body = "\n".join(body_lines)
    slug = _slugify(title, fallback=video_id.lower())
    artifact_path = None if dry_run else _write_ingested_markdown("youtube", slug, title, source_url, body)
    return {
        "title": title,
        "preview": f"YouTube transcript placeholder for {video_id}",
        "artifact_path": str(artifact_path.relative_to(ROOT)) if artifact_path else "",
        "entry_url": source_url,
        "publisher": str(feed_config.get("publisher") or "YouTube"),
        "topics": list(feed_config.get("topics", [])),
        "classified_by": "baoyu-youtube-transcript-wrapper",
    }


# ── 피드 처리 ─────────────────────────────────────

def fetch_feed(url: str, timeout: int = NETWORK_TIMEOUT) -> list[Any]:
    """RSS/Atom 피드 fetch. 실패 시 빈 리스트 + stderr 로그."""
    if feedparser is None:
        raise RuntimeError("feedparser 미설치 — `pip install feedparser`")

    # feedparser는 자체 timeout 지원 안함 → urllib로 우회
    try:
        import socket
        socket.setdefaulttimeout(timeout)
        # feedparser가 requests 없이도 HTTP fetch 가능 (내장)
        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            print(f"[warn] 피드 파싱 실패: {url} ({parsed.bozo_exception})", file=sys.stderr)
            return []
        return list(parsed.entries or [])
    except Exception as exc:
        print(f"[error] 피드 fetch 실패: {url} — {exc}", file=sys.stderr)
        return []


def classify_entry(title: str, summary: str, feed_config: dict[str, Any]) -> dict[str, Any]:
    """
    Haiku 4.5 호출로 topic 분류 (선택).
    API 키 없거나 실패 시 feed_config.topics 그대로 반환.
    """
    default_topics = feed_config.get("topics", [])
    result = {
        "topics": default_topics,
        "relevance_score": 0.5,
        "classified_by": "default",
    }

    # API provider 사용 시에만 API 키 체크 (SDK·mock은 불필요)
    kind = (os.environ.get("CLAUDE_PROVIDER", "api")).lower()
    if kind == "api" and not os.environ.get("ANTHROPIC_API_KEY"):
        return result

    try:
        try:
            from pipeline.claude_provider import get_provider
        except ModuleNotFoundError:
            from claude_provider import get_provider  # type: ignore

        provider = get_provider()

        system_prompt = "JSON으로만 답하고 다른 텍스트는 출력하지 않는다."
        user_prompt = (
            f"다음 피드 entry를 분류하세요.\n\n"
            f"피드: {feed_config.get('name', '')}\n"
            f"기본 토픽: {', '.join(default_topics)}\n\n"
            f"제목: {title}\n"
            f"요약: {summary[:300]}\n\n"
            f"다음 JSON 형태로만 답하세요:\n"
            f'{{"topics": ["topic1","topic2"], "relevance": 0.0~1.0}}'
        )

        resp = provider.stream_complete(
            system=system_prompt,
            user=user_prompt,
            model_tier="haiku",
            max_tokens=150,
        )

        text = resp.text or "{}"
        import re
        match = re.search(r"\{[^}]+\}", text)
        if match:
            parsed = json.loads(match.group(0))
            result["topics"] = parsed.get("topics", default_topics)
            result["relevance_score"] = float(parsed.get("relevance", 0.5))
            result["classified_by"] = f"haiku-via-{resp.provider}"
    except Exception as exc:
        print(f"[warn] 분류 실패 ({title[:40]}...): {exc}", file=sys.stderr)

    return result


def detect_duplicate(entry_url: str) -> str | None:
    """source_registry 내 URL 존재 확인. 있으면 source_id 반환."""
    try:
        import sqlite3
        db_path = os.environ.get("SOURCE_DB_PATH") or str(ROOT / "data" / "source_registry.db")
        if not Path(db_path).exists():
            return None
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT source_id FROM sources WHERE url = ?", (entry_url,)
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    except Exception:
        return None


# ── 메인 ──────────────────────────────────────────

def ingest_feeds(
    feeds_path: str | Path = DEFAULT_FEEDS,
    since_days: int | None = None,
    feed_filter: str | None = None,
    dry_run: bool = False,
    auto_classify: bool = True,
) -> dict[str, Any]:
    """
    피드 수집 메인 루프.
    반환: 통계 dict (TASK_032.md 명세 참고)
    """
    feeds = _load_feeds(feeds_path)
    if feed_filter:
        feeds = [f for f in feeds if f.get("name") == feed_filter]

    state = _load_state()
    now = datetime.now(timezone.utc)

    summary: dict[str, Any] = {
        "period": {"to": now.isoformat()},
        "feeds_processed": 0,
        "entries_fetched": 0,
        "entries_new": 0,
        "entries_duplicate": 0,
        "entries_registered": 0,
        "entries_skipped": 0,
        "details": [],
        "dry_run": dry_run,
    }

    if since_days is not None:
        # state 무시하고 N일 전부터 강제 재수집
        from datetime import timedelta
        cutoff = now - timedelta(days=since_days)
        summary["period"]["from"] = cutoff.isoformat()
    else:
        summary["period"]["from"] = "last_state"

    # source_registry import (lazy — 모듈 로딩 시 순환 참조 방지)
    try:
        from pipeline.source_registry import add_source, init_db
        init_db()
    except Exception as exc:
        print(f"[error] source_registry import 실패: {exc}", file=sys.stderr)
        return summary

    for feed_config in feeds:
        name = feed_config.get("name", "unknown")
        url = feed_config.get("url", "")
        feed_type = str(feed_config.get("type", "rss")).lower()
        if not url:
            continue

        summary["feeds_processed"] += 1
        detail: dict[str, Any] = {"feed": name, "type": feed_type, "new": 0, "dup": 0, "errors": []}

        if feed_type in {"url", "youtube"}:
            summary["entries_fetched"] += 1
            existing_id = detect_duplicate(url)
            if existing_id:
                summary["entries_duplicate"] += 1
                detail["dup"] += 1
                summary["details"].append(detail)
                print(f"[{summary['feeds_processed']}/{len(feeds)}] {name}\n  ⏭  중복 URL — {existing_id}\n")
                continue

            try:
                if feed_type == "url":
                    processed = ingest_url(feed_config, dry_run=dry_run)
                else:
                    processed = ingest_youtube(feed_config, dry_run=dry_run)
            except Exception as exc:
                detail["errors"].append(f"{feed_type} 처리 실패: {exc}")
                summary["entries_skipped"] += 1
                summary["details"].append(detail)
                print(f"[{summary['feeds_processed']}/{len(feeds)}] {name}\n  ❌ {exc}\n")
                continue

            detail["new"] += 1
            summary["entries_new"] += 1
            print(f"  - {processed['title'][:60]}{'...' if len(processed['title']) > 60 else ''}")

            if not dry_run:
                try:
                    add_source(
                        url=processed["entry_url"],
                        publisher=processed["publisher"],
                        content_preview=processed["preview"],
                        rights_status="unknown",
                        language=feed_config.get("language", "unknown"),
                        stance=feed_config.get("stance", "neutral"),
                        is_official=bool(feed_config.get("is_official", False)),
                    )
                    summary["entries_registered"] += 1
                except Exception as exc:
                    detail["errors"].append(f"등록 실패: {exc}")
                    summary["entries_skipped"] += 1
            summary["details"].append(detail)
            print(
                f"[{summary['feeds_processed']}/{len(feeds)}] {name}\n"
                f"  📥 1건 조회 / {detail['new']}건 신규 / {detail['dup']}건 기존\n"
            )
            continue

        # state 기준 cutoff 결정
        if since_days is not None:
            cutoff = now - __import__("datetime").timedelta(days=since_days)
        else:
            last_iso = state.get(name)
            if last_iso:
                try:
                    cutoff = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
                except ValueError:
                    cutoff = None  # type: ignore
            else:
                cutoff = None  # 처음 수집 — 전체 기록

        entries = fetch_feed(url)
        summary["entries_fetched"] += len(entries)

        new_in_feed = []
        for entry in entries:
            published = _parse_published(entry)
            if cutoff is not None and published is not None and published <= cutoff:
                continue
            new_in_feed.append(entry)

        for entry in new_in_feed:
            entry_url = getattr(entry, "link", None) or (entry.get("link") if hasattr(entry, "get") else "")
            if not entry_url:
                summary["entries_skipped"] += 1
                continue

            # 중복 체크 (1차: DB URL 일치)
            existing_id = detect_duplicate(entry_url)
            if existing_id:
                summary["entries_duplicate"] += 1
                detail["dup"] += 1
                continue

            # 분류
            title = getattr(entry, "title", "") or ""
            preview = _entry_preview(entry)
            if auto_classify:
                classification = classify_entry(title, preview, feed_config)
            else:
                classification = {
                    "topics": feed_config.get("topics", []),
                    "relevance_score": 0.5,
                    "classified_by": "default",
                }

            summary["entries_new"] += 1
            detail["new"] += 1

            print(
                f"  - {title[:60]}{'...' if len(title) > 60 else ''} "
                f"→ topics={classification['topics']}"
            )

            if dry_run:
                continue

            try:
                add_source(
                    url=entry_url,
                    publisher=name,
                    content_preview=preview,
                    rights_status="unknown",
                    language=feed_config.get("language", "unknown"),
                    stance=feed_config.get("stance", "neutral"),
                    is_official=bool(feed_config.get("is_official", False)),
                )
                summary["entries_registered"] += 1
            except Exception as exc:
                detail["errors"].append(f"등록 실패: {exc}")
                summary["entries_skipped"] += 1

        # 피드별 state 업데이트 (성공 시에만)
        if not dry_run and not detail["errors"]:
            state[name] = now.isoformat()

        summary["details"].append(detail)

        print(
            f"[{summary['feeds_processed']}/{len(feeds)}] {name}\n"
            f"  📥 {len(entries)}건 조회 / {detail['new']}건 신규 / {detail['dup']}건 기존\n"
        )

    if not dry_run:
        _save_state(state)

    return summary


# ── 스모크 테스트 ──────────────────────────────────

def _smoke_test() -> int:
    """인자 없이 실행 시 내장 스모크 테스트 (네트워크 호출 없음)."""
    print("=== source_ingester 스모크 테스트 ===\n")

    checks = []

    # 1. feedparser import
    checks.append(("feedparser 모듈", feedparser is not None))

    # 2. yaml import
    checks.append(("PyYAML 모듈", yaml is not None))

    # 3. feeds.yml 존재
    checks.append(("config/feeds.yml", DEFAULT_FEEDS.exists()))

    # 4. feeds.yml 로드 가능
    feeds_loadable = False
    try:
        feeds = _load_feeds(DEFAULT_FEEDS)
        feeds_loadable = len(feeds) > 0
    except Exception as e:
        print(f"   loadable error: {e}", file=sys.stderr)
    checks.append(("feeds 로드 (enabled 1+)", feeds_loadable))

    # 4.5 url/youtube 타입 스키마 지원
    has_ext_types = False
    try:
        raw_config = DEFAULT_FEEDS.read_text(encoding="utf-8")
        has_ext_types = "type: url" in raw_config and "type: youtube" in raw_config
    except Exception:
        has_ext_types = False
    checks.append(("feeds 확장 타입(url/youtube) 지원", has_ext_types))

    # 5. state 경로 생성 가능
    state_writable = False
    try:
        _save_state({})
        state_writable = STATE_PATH.exists()
    except Exception:
        pass
    checks.append(("state 파일 쓰기", state_writable))

    # 6. source_registry import
    sr_loadable = False
    try:
        from pipeline.source_registry import add_source  # noqa
        sr_loadable = True
    except Exception:
        pass
    checks.append(("source_registry 연결", sr_loadable))

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)

    for idx, (name, ok) in enumerate(checks, 1):
        status = "✅" if ok else "❌"
        print(f"[{idx}/{total}] {status} {name}")

    print(f"\n=== 스모크 결과: {passed}/{total} 통과 ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    # 직접 실행 호환 — 프로젝트 루트를 path에 추가
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    sys.exit(_smoke_test())
