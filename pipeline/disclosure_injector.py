"""
AI 사용 고지 자동 삽입 (TASK_018)
모든 발행 기사 하단에 AI 사용 고지 문구를 자동 삽입.

사용법:
  # HTML 파일 처리
  python pipeline/disclosure_injector.py --html article.html --output article_disclosed.html

  # 템플릿 지정
  python pipeline/disclosure_injector.py --html article.html --output out.html --template heavy

  # Ghost 포스트 ID 직접 업데이트
  python pipeline/disclosure_injector.py --ghost-post-id POST_ID --template light
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

# Windows 환경에서 한국어/특수문자 출력을 위한 UTF-8 강제 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

DISCLOSURE_VERSION = "1.0"
DEFAULT_HEAVY_MODELS = ("claude-sonnet-4-6", "claude-opus-4-7")
VALID_TEMPLATES = ("light", "heavy", "interview")

_LIGHT_TEMPLATE = f"""<div class="ai-disclosure" data-version="{DISCLOSURE_VERSION}">
  <p>이 기사는 Claude AI 보조 도구를 사용해 작성되었습니다.
     최종 편집 책임은 Claude Magazine 편집팀에 있습니다.</p>
  <p>정정 요청: editorial@claude-magazine.kr (24시간 내 1차 응답)</p>
</div>"""

_HEAVY_TEMPLATE = f"""<div class="ai-disclosure" data-version="{DISCLOSURE_VERSION}">
  <h4>AI 사용 고지</h4>
  <ul>
    <li>브리프·초안 작성: claude-sonnet-4-6</li>
    <li>팩트체크: claude-opus-4-7</li>
    <li>데이터 분석: {{{{used_models}}}}</li>
  </ul>
  <p>모든 수치·인용은 편집자가 원문과 대조 검증했습니다.
     출처는 각 문장 말미의 [src-xxx] 참조.</p>
  <p>정정 요청: editorial@claude-magazine.kr (24시간 내 1차 응답)</p>
</div>"""

_INTERVIEW_TEMPLATE = f"""<div class="ai-disclosure" data-version="{DISCLOSURE_VERSION}">
  <p>본 인터뷰는 편집팀이 직접 진행했으며,
     녹취 정리·초안 구성에 Claude AI 보조 도구를 사용했습니다.</p>
  <p>인터뷰이 발언은 AI 생성이 아닌 원문 녹취 기반입니다.</p>
  <p>정정 요청: editorial@claude-magazine.kr (24시간 내 1차 응답)</p>
</div>"""

_TEMPLATES = {
    "light": _LIGHT_TEMPLATE,
    "heavy": _HEAVY_TEMPLATE,
    "interview": _INTERVIEW_TEMPLATE,
}


def get_template(name: str) -> str:
    """템플릿 조회 — light | heavy | interview"""
    if name not in _TEMPLATES:
        raise ValueError(
            f"알 수 없는 템플릿: {name!r}. 사용 가능: {', '.join(VALID_TEMPLATES)}"
        )
    return _TEMPLATES[name]


def _render_template(name: str, used_models: list[str] | None = None) -> str:
    """템플릿 렌더링 (heavy의 {{used_models}} placeholder 치환)"""
    tpl = get_template(name)
    if name == "heavy":
        models = used_models if used_models else list(DEFAULT_HEAVY_MODELS)
        tpl = tpl.replace("{{used_models}}", ", ".join(models))
    return tpl


def inject_disclosure(
    html: str,
    template: str = "light",
    used_models: list[str] | None = None,
) -> str:
    """
    기존 HTML 하단에 고지 삽입, 중복 삽입 방지.

    - `<div class="ai-disclosure" data-version="X.Y">` 패턴 존재 시 제거 후 교체
    - 이렇게 하면 템플릿 변경 시 전체 기사에 재적용 가능
    """
    if template not in VALID_TEMPLATES:
        raise ValueError(
            f"알 수 없는 템플릿: {template!r}. 사용 가능: {', '.join(VALID_TEMPLATES)}"
        )

    soup = BeautifulSoup(html, "html.parser")

    # 1. 기존 ai-disclosure 전부 제거 (중복 방지)
    for existing in soup.find_all("div", class_="ai-disclosure"):
        existing.decompose()

    # 2. 새 고지 블록 생성
    disclosure_html = _render_template(template, used_models=used_models)
    disclosure_fragment = BeautifulSoup(disclosure_html, "html.parser")

    # 3. 삽입 위치 결정
    #    - <article>이 있으면 그 끝에 append
    #    - <body>가 있으면 그 끝에 append
    #    - 둘 다 없으면 문서 루트 끝에 append
    anchor = soup.find("article") or soup.find("body") or soup
    anchor.append(disclosure_fragment)

    return str(soup)


def _has_existing_disclosure(html: str) -> tuple[bool, str | None]:
    """기존 고지 존재 여부 및 버전 감지"""
    soup = BeautifulSoup(html, "html.parser")
    existing = soup.find("div", class_="ai-disclosure")
    if existing is None:
        return False, None
    version = existing.get("data-version")
    return True, version


def update_ghost_post(post_id: str, template: str = "light") -> dict[str, Any]:
    """
    Ghost API로 포스트 HTML fetch → 고지 삽입 → PUT 업데이트.

    반환: {"post_id": str, "updated_at": str, "disclosure_version": str}
    """
    # Lazy import — API 키 없이도 기본 HTML 조작은 가능해야 함
    try:
        from pipeline.ghost_client import _request  # type: ignore
    except ModuleNotFoundError:
        from ghost_client import _request  # type: ignore

    if not (os.getenv("GHOST_ADMIN_API_URL") and os.getenv("GHOST_ADMIN_API_KEY")):
        raise RuntimeError(
            "Ghost API 키가 설정되지 않았습니다. "
            "GHOST_ADMIN_API_URL, GHOST_ADMIN_API_KEY를 .env에 설정하세요."
        )

    # 1. 포스트 fetch
    response = _request("GET", f"/posts/{post_id}/", params={"formats": "html"})
    post = response["posts"][0]
    original_html = post.get("html") or ""
    updated_at = post["updated_at"]

    # 2. 고지 삽입
    new_html = inject_disclosure(original_html, template=template)

    # 3. PUT 업데이트
    payload = {
        "posts": [
            {
                "updated_at": updated_at,
                "html": new_html,
            }
        ]
    }
    put_response = _request(
        "PUT",
        f"/posts/{post_id}/",
        params={"source": "html"},
        payload=payload,
    )
    updated_post = put_response["posts"][0]
    return {
        "post_id": updated_post["id"],
        "updated_at": updated_post["updated_at"],
        "disclosure_version": DISCLOSURE_VERSION,
    }


def _process_file(
    input_path: Path,
    output_path: Path,
    template: str,
    used_models: list[str] | None,
) -> None:
    original = input_path.read_text(encoding="utf-8")
    existed, old_version = _has_existing_disclosure(original)
    result = inject_disclosure(original, template=template, used_models=used_models)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result, encoding="utf-8")

    delta = len(result.encode("utf-8")) - len(original.encode("utf-8"))
    sign = "+" if delta >= 0 else ""

    print("=== AI 사용 고지 삽입 ===")
    print(f"입력: {input_path}")
    print(f"템플릿: {template}")
    if template == "heavy":
        models = used_models if used_models else list(DEFAULT_HEAVY_MODELS)
        print(f"사용 모델: {', '.join(models)}")
    if existed:
        print(f"✅ 기존 고지 v{old_version} 발견 — 제거 후 v{DISCLOSURE_VERSION} 재삽입")
    else:
        print(f"✅ 신규 고지 v{DISCLOSURE_VERSION} 삽입")
    print(f"✅ 출력 저장: {output_path} ({sign}{delta} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI 사용 고지 자동 삽입 (disclosure_injector)"
    )
    parser.add_argument("--html", type=Path, help="입력 HTML 파일 경로")
    parser.add_argument("--output", type=Path, help="출력 HTML 파일 경로")
    parser.add_argument(
        "--template",
        choices=VALID_TEMPLATES,
        default="light",
        help="고지 템플릿 선택 (기본: light)",
    )
    parser.add_argument(
        "--used-models",
        nargs="+",
        default=None,
        help="heavy 템플릿에서 사용할 모델 목록 (공백 구분)",
    )
    parser.add_argument(
        "--ghost-post-id",
        help="Ghost 포스트 ID로 직접 업데이트",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 파일/Ghost 변경 없이 동작 확인",
    )
    args = parser.parse_args()

    # Ghost 포스트 직접 업데이트
    if args.ghost_post_id:
        if args.dry_run:
            print("[dry-run] Ghost 포스트 업데이트 스킵:")
            print(f"  post_id={args.ghost_post_id}, template={args.template}")
            return 0
        result = update_ghost_post(args.ghost_post_id, template=args.template)
        print("=== Ghost 포스트 업데이트 완료 ===")
        print(result)
        return 0

    # HTML 파일 처리
    if not args.html:
        parser.error("--html 또는 --ghost-post-id 중 하나는 반드시 지정해야 합니다.")
    if not args.output:
        parser.error("--html 사용 시 --output을 반드시 지정해야 합니다.")
    if not args.html.exists():
        parser.error(f"입력 파일을 찾을 수 없습니다: {args.html}")

    if args.dry_run:
        original = args.html.read_text(encoding="utf-8")
        result = inject_disclosure(
            original, template=args.template, used_models=args.used_models
        )
        print("[dry-run] 아래 내용을 파일에 쓰지 않습니다:")
        print(result)
        return 0

    _process_file(args.html, args.output, args.template, args.used_models)
    return 0


if __name__ == "__main__":
    # 스모크 테스트 모드 — 인자 없이 호출 시
    if len(sys.argv) == 1:
        print("=== 스모크 테스트 ===")
        sample = "<article><h1>테스트</h1><p>본문</p></article>"

        print("\n[1] light 템플릿")
        out_light = inject_disclosure(sample, template="light")
        assert 'class="ai-disclosure"' in out_light
        assert f'data-version="{DISCLOSURE_VERSION}"' in out_light
        print(out_light)

        print("\n[2] heavy 템플릿 (모델 명시)")
        out_heavy = inject_disclosure(
            sample,
            template="heavy",
            used_models=["claude-sonnet-4-6", "claude-opus-4-7"],
        )
        assert "claude-sonnet-4-6, claude-opus-4-7" in out_heavy
        print(out_heavy)

        print("\n[3] interview 템플릿")
        out_interview = inject_disclosure(sample, template="interview")
        assert "인터뷰이 발언은 AI 생성이 아닌" in out_interview
        print(out_interview)

        print("\n[4] 중복 방지 — light 출력에 다시 삽입")
        out_reinject = inject_disclosure(out_light, template="light")
        count = out_reinject.count('class="ai-disclosure"')
        assert count == 1, f"ai-disclosure 개수 예상 1, 실제 {count}"
        print(f"✅ ai-disclosure 개수: {count} (중복 방지 OK)")

        print("\n모든 스모크 테스트 통과")
        sys.exit(0)

    raise SystemExit(main())
