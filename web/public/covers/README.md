# 월간 커버 이미지

이 폴더에 월별 커버 일러스트를 드롭인하면 `CoverPage.jsx`가 자동으로 참조한다.
Vite 는 `web/public/` 하위 파일을 빌드 시 그대로 `dist/covers/` 로 복사하므로 별도 import 구문이 필요 없다.

## 파일명 규칙
- **월별 기본**: `YYYY-MM.png` (예: `2026-05.png`)
- **Retina**: `YYYY-MM@2x.png` — 2배 해상도 (선택)
- **변형**: `YYYY-MM-variant-{name}.png` — 테마 A/B (선택)
- **Fallback**: `default.png` — **필수 · 삭제 금지**

`CoverPage.jsx` 의 `resolveCoverPath(issueDate)` 가 `"2026년 5월"` 같은 한국어 날짜를 `YYYY-MM` 으로 정규화해 `/covers/YYYY-MM.png` 를 조회한다. 파일이 없거나 로드 에러 시 `<img onError>` 가 `/covers/default.png` 로 자동 대체한다.

## 권장 사이즈
| 포맷       | 크기          | 비고                                   |
|------------|---------------|----------------------------------------|
| 표준       | 800×550 px    | `CoverPage` 우하단 블록과 동일 비율    |
| Retina     | 1600×1100 px  | `@2x.png` 접미사                       |
| 포맷       | PNG 또는 WebP | 권장 용량 ≤ 500KB (PDF 시간 영향 최소) |

## 라이선스 기록 (필수)
이미지를 커밋할 때마다 `web/public/covers/licenses.json` 에 엔트리를 추가한다.
`scripts/check_covers.py` 가 누락을 경고하고, TASK_016 (`editorial_lint`) 의 `image-rights` 체크가 실제로 탐지한다.

```json
{
  "2026-05.png": {
    "source": "Claude Design / claude.ai/design",
    "created_at": "2026-04-22",
    "rights": "internal-use-only",
    "prompt": "네이비 배경 + 코랄 포인트 추상 기하학",
    "created_by": "editor-name"
  }
}
```

### 필드 설명
- `source`: 생성 도구/작가 (예: `"Claude Design"`, `"Midjourney v6"`, `"직접 제작"`)
- `created_at`: 생성일 `YYYY-MM-DD`
- `rights`: `internal-use-only` · `cc-by-4.0` · `purchased-license` 중 하나
- `prompt`: 생성 프롬프트 원문 (재현성 확보)
- `created_by`: 담당 에디터 이름/핸들

## 검증
```bash
python scripts/check_covers.py
```
- `default.png` 존재 확인
- `licenses.json` ↔ 실제 파일 cross-check
- 다음 월 커버 미등록 경고
