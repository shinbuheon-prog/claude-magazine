# TASK_023 — SNS 카드뉴스 자산 배포 파이프라인

## 메타
- **status**: todo
- **prerequisites**: TASK_021 (이미지 자산 경로 컨벤션)
- **예상 소요**: 45분
- **서브에이전트 분할**: 불필요
- **Phase**: 3 (배포 채널 확장)

---

## 목적
현재 `channel_rewriter.py`는 **텍스트 재가공만** 수행. SNS 발행은 비주얼이 필수.
Claude Design(또는 외부 도구)으로 제작한 카드뉴스 이미지를 **구조화된 경로**에 저장하고,
`channel_rewriter.py` 출력에 **이미지 경로를 포함**시켜 즉시 배포 가능한 번들을 만든다.

우선순위 3: 도달 확장 (무료 매거진일수록 SNS 배포가 인바운드 핵심).

---

## 구현 명세

### 1. 폴더 컨벤션
```
web/public/sns/
├── README.md                                ← 파일명·사이즈 규칙
├── licenses.json                            ← 라이선스 추적
└── YYYY-MM/                                 ← 월별 폴더
    ├── {post-slug}-card-01.png              ← 카드뉴스 N장 시리즈
    ├── {post-slug}-card-02.png
    ├── {post-slug}-linkedin-header.png      ← LinkedIn 1200×627
    ├── {post-slug}-og.png                   ← Open Graph 1200×630
    └── {post-slug}-quote.png                ← 인용 이미지 1080×1080
```

### 2. 사이즈 표준
| 용도 | 권장 사이즈 | 포맷 |
|---|---|---|
| Instagram 카드 | 1080×1080 | PNG |
| Instagram 스토리 | 1080×1920 | PNG |
| LinkedIn 포스트 | 1200×627 | PNG |
| Twitter/X 카드 | 1200×675 | PNG |
| Open Graph | 1200×630 | PNG |
| 인용 이미지 | 1080×1080 | PNG |

### 3. channel_rewriter.py 확장

기존 시그니처 유지하고 반환 구조 확장:
```python
def rewrite_for_channel(
    draft_text: str,
    channel: str,          # "sns" | "linkedin" | "twitter" | "instagram"
    post_slug: str,        # 파일명 매칭용
    month: str | None = None,  # "2026-05", 없으면 현재월
) -> dict:
    """
    반환: {
        "channel": str,
        "text": str,
        "assets": [
            {"path": "web/public/sns/2026-05/post-slug-card-01.png",
             "exists": bool,
             "size": str,
             "alt": str},
            ...
        ],
        "missing_assets": [str],  # 예상 경로 중 파일 없는 것
        "recommendations": [str],
    }
    """
```

동작:
1. 기존대로 Haiku로 텍스트 재가공
2. 채널별로 **기대 이미지 경로 목록 생성** (예: sns → card-01, card-02)
3. 각 경로에 대해 `os.path.exists()` 검사
4. 존재하는 자산: 메타데이터 포함하여 반환
5. 미존재 자산: `missing_assets`에 열거 + 권고 메시지

### 4. 신규 CLI 옵션
```bash
# 기존
python pipeline/channel_rewriter.py --draft article.md --channel sns

# 신규
python pipeline/channel_rewriter.py --draft article.md --channel sns \
    --post-slug claude-4-launch \
    --month 2026-05 \
    --assets-report  # 자산 존재 여부만 빠르게 출력
```

### 5. 출력 형식
```
=== Channel Rewriter (sns) ===

재가공 텍스트:
  (Haiku 출력 표시)

자산 체크 (web/public/sns/2026-05/claude-4-launch-*):
  ✅ card-01.png  (1080×1080, 245KB)  alt="Claude 4 출시 표지"
  ✅ card-02.png  (1080×1080, 198KB)  alt="모델 계층 분포"
  ❌ card-03.png  (미존재)
  ❌ og.png      (미존재)

권고:
  - card-03.png, og.png 2개 이미지 추가 제작 필요
  - Claude Design 링크: claude.ai/design
  - 라이선스 등록: web/public/sns/licenses.json
```

### 6. `scripts/check_sns_assets.py`
TASK_021의 `check_covers.py`와 동일 패턴:
```bash
python scripts/check_sns_assets.py --month 2026-05
python scripts/check_sns_assets.py --post-slug claude-4-launch --month 2026-05
```
- licenses.json 과 실제 파일 대조
- 누락 파일 리포트
- 고아 파일(라이선스 없는) 경고

### 7. web/public/sns/README.md 생성
- 월별 폴더 컨벤션
- 파일명 규칙 (`{slug}-{type}-{nn}.png`)
- 권장 사이즈 표
- 라이선스 등록 방법

### 8. web/public/sns/licenses.json (빈 객체로 시작)

---

## 완료 조건
- [ ] `web/public/sns/` 폴더 구조 생성
- [ ] `web/public/sns/README.md`, `licenses.json` 생성
- [ ] `pipeline/channel_rewriter.py` 확장 — `assets`, `missing_assets` 반환
- [ ] 새 CLI 옵션 `--post-slug`, `--month`, `--assets-report` 동작
- [ ] `scripts/check_sns_assets.py` 생성 및 동작 확인
- [ ] 채널별 기대 자산 매핑 dict 정의 (sns/linkedin/twitter/instagram)
- [ ] 스모크 테스트: 가짜 draft + 가짜 이미지 1장 → 자산 체크 결과 정확
- [ ] 기존 `channel_rewriter.py`의 단순 텍스트 호출도 하위 호환 유지

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_023 implemented
```

---

## 주의사항
- 이미지 자체를 **생성하지 않음** — 경로 관리와 체크만
- Claude Design은 API 없음 → 수동 업로드 경로만 표준화
- `missing_assets` 리포트에서 Claude Design URL 안내 문구 포함
- `assets` 경로는 React `public/` 상대 경로로 노출하되, 파일시스템 체크는 절대 경로로
- TASK_016 (editorial_lint)의 `image-rights` 검사와 licenses.json 연동 가능
- 이미지 메타데이터 (크기, 해상도)는 `Pillow` 사용 — requirements.txt에 없으면 추가
