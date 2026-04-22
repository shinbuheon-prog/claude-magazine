# SNS 카드뉴스 자산

Claude Magazine SNS 배포용 이미지 자산 저장소.
`pipeline/channel_rewriter.py` 가 채널별 텍스트 재가공과 함께 이 폴더의 이미지 경로를 번들링한다.
Vite 는 `web/public/` 하위 파일을 빌드 시 그대로 `dist/sns/` 로 복사한다.

## 폴더 구조
```
web/public/sns/
├── README.md                             ← 이 파일
├── licenses.json                         ← 라이선스 추적 (필수)
└── YYYY-MM/                              ← 월별 폴더 (발행 시 생성)
    ├── {post-slug}-card-01.png           ← SNS 카드뉴스 시리즈
    ├── {post-slug}-card-02.png
    ├── {post-slug}-card-03.png
    ├── {post-slug}-story.png             ← Instagram 스토리
    ├── {post-slug}-linkedin-header.png   ← LinkedIn 헤더
    ├── {post-slug}-twitter-card.png      ← Twitter/X 카드
    ├── {post-slug}-og.png                ← Open Graph
    └── {post-slug}-quote.png             ← 인용 이미지
```

## 파일명 규칙
- **형식**: `{post-slug}-{type}[-{nn}].png`
- **post-slug**: 소문자, 하이픈만 (공백/한글 금지)
- **type**: `card`, `story`, `linkedin-header`, `twitter-card`, `og`, `quote`
- **nn**: 시리즈일 경우 2자리 번호 (`-01`, `-02`, ...)

예: `claude-4-launch-card-01.png`

## 권장 사이즈
| 용도 | 권장 사이즈 | 포맷 | 비고 |
|---|---|---|---|
| SNS 카드 (공통) | 1080×1080 | PNG | 정사각형 |
| Instagram 피드 | 1080×1080 | PNG | card-01 와 동일 |
| Instagram 스토리 | 1080×1920 | PNG | 세로 9:16 |
| LinkedIn 포스트 | 1200×627 | PNG | 가로 1.91:1 |
| Twitter/X 카드 | 1200×675 | PNG | 가로 16:9 |
| Open Graph | 1200×630 | PNG | 가로 1.91:1 |
| 인용 이미지 | 1080×1080 | PNG | 정사각형 |

권장 용량: ≤ 500KB (SNS 플랫폼 자동 압축 손실 최소화)

## 채널별 기대 자산
`pipeline/channel_rewriter.py::CHANNEL_ASSETS` 에 정의된 매핑:

| 채널 | 기대 자산 |
|---|---|
| `sns` | card-01, card-02, card-03, og, quote |
| `instagram` | card-01, story, quote |
| `linkedin` | linkedin-header, og |
| `twitter` | twitter-card, quote |

## 라이선스 기록 (필수)
이미지를 커밋할 때마다 `licenses.json` 에 엔트리를 추가한다.
`scripts/check_sns_assets.py` 가 누락을 경고하고,
TASK_016 (`editorial_lint`) 의 `image-rights` 체크가 탐지한다.

```json
{
  "2026-05/claude-4-launch-card-01.png": {
    "source": "Claude Design / claude.ai/design",
    "created_at": "2026-04-22",
    "rights": "internal-use-only",
    "prompt": "Claude 4 출시 표지 — 네이비 배경 + 코랄 포인트",
    "created_by": "editor-name",
    "size": "1080x1080",
    "alt": "Claude 4 출시 표지"
  }
}
```

### 필드 설명
- `source`: 생성 도구/작가 (예: `"Claude Design"`, `"Midjourney v6"`, `"직접 제작"`)
- `created_at`: 생성일 `YYYY-MM-DD`
- `rights`: `internal-use-only` · `cc-by-4.0` · `purchased-license` 중 하나
- `prompt`: 생성 프롬프트 원문 (재현성 확보)
- `created_by`: 담당 에디터 이름/핸들
- `size`: 이미지 사이즈 (예: `"1080x1080"`)
- `alt`: 대체 텍스트 (접근성)

키 형식은 월별 폴더 기준의 **상대 경로** (`YYYY-MM/filename.png`).

## 제작 가이드
Claude Design: <https://claude.ai/design>
브랜드 토큰: `web/src/theme.js` 참조 (navy #0F172A, coral #F97316)

## 검증
```bash
# 전체 월 검사
python scripts/check_sns_assets.py --month 2026-05

# 특정 포스트 자산만 검사
python scripts/check_sns_assets.py --month 2026-05 --post-slug claude-4-launch

# 자산 존재 여부만 (channel_rewriter.py 에 내장)
python pipeline/channel_rewriter.py --draft article.md --channel sns \
    --post-slug claude-4-launch --month 2026-05 --assets-report
```
