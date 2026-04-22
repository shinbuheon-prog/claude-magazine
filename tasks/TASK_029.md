# TASK_029 — 편집자 승인 UI (스캐폴딩 제거)

## 메타
- **status**: todo
- **prerequisites**: TASK_002 (Ghost API), TASK_016 (editorial_lint)
- **예상 소요**: 90분
- **서브에이전트 분할**: 가능 (A: 백엔드 API / B: React UI)
- **Phase**: 4 (스캐폴딩 제거)

---

## 목적
Miessler "Most Work is Scaffolding" 원칙 적용.

> "지식 작업의 75-99%는 도구, 워크플로, 템플릿 유지."

**현재 남은 스캐폴딩**: 편집자가 n8n webhook URL을 수동으로 호출해 발행. 승인 UI·취소·롤백·비교 UI 없음.
**목표**: 드래프트 목록 → 비교 뷰 → editorial_lint 결과 확인 → 한 번에 발행.

---

## 구현 명세

### 1. 생성 파일
```
scripts/
└── editor_api_server.py         ← FastAPI 로컬 서버 (포트 8080)

web/src/pages/admin/
├── DraftListPage.jsx             ← 드래프트 목록
├── DraftReviewPage.jsx           ← 비교·검증·승인 뷰
└── PublishHistoryPage.jsx        ← 발행 이력 + 롤백

web/src/api/
└── admin.js                      ← editor_api 클라이언트
```

### 2. `scripts/editor_api_server.py` (FastAPI)

엔드포인트:
```
GET  /api/drafts                       # drafts/ + Ghost drafts 통합 목록
GET  /api/drafts/{article_id}          # 단건 조회 (Markdown + metadata)
GET  /api/drafts/{article_id}/lint     # editorial_lint 결과 (실시간)
GET  /api/drafts/{article_id}/diff     # 원본 brief vs 최종 draft diff

POST /api/drafts/{article_id}/approve  # 승인 → Ghost publish + newsletter
POST /api/drafts/{article_id}/reject   # 반려 (editor_corrections에 기록 옵션)

GET  /api/published                    # Ghost published posts
POST /api/published/{post_id}/unpublish # 롤백 → status=draft
```

인증:
- 로컬 실행 전용 (127.0.0.1 바인딩만)
- 또는 `EDITOR_API_TOKEN` 환경변수 체크

### 3. 드래프트 목록 (`DraftListPage.jsx`)

```
┌─────────────────────────────────────────────────────┐
│ 📝 드래프트 (12건)  [새로고침] [필터: 카테고리▾]    │
├─────────────────────────────────────────────────────┤
│ ┌─ Claude 4 실무 전략 ──── DEEP DIVE ─── 2시간 전 ─┐│
│ │ ⚠️  lint 7/10 · standards 4/6                    ││
│ │ source 12 · words 2,340                          ││
│ │                          [검토] [삭제]           ││
│ └──────────────────────────────────────────────────┘│
│ ┌─ AI 엔지니어 인터뷰 ──── INTERVIEW ─── 1일 전 ──┐│
│ │ ✅ lint 10/10 · standards 5/5                    ││
│ │ 인용 9 · Q&A 6                                   ││
│ │                          [검토] [승인] [삭제]    ││
│ └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

### 4. 드래프트 검토 뷰 (`DraftReviewPage.jsx`)

```
┌───────────────────────────────────────────────────────┐
│ ← 돌아가기   Claude 4 실무 전략              [승인]   │
├───────────────────────────────────────────────────────┤
│ ┌─ lint ─────────┐ ┌─ standards ─────┐ ┌─ diversity ─┐│
│ │ ✅ source-id   │ │ ⚠️ source-count │ │ ✅ 언어     ││
│ │ ❌ image-right │ │ ✅ quantitative │ │ ⚠️ 관점     ││
│ │ ✅ disclosure  │ │ ❌ counter-pers.│ │ ✅ 발행처    ││
│ │ 7/10           │ │ 4/6             │ │ 3/4         ││
│ └────────────────┘ └─────────────────┘ └─────────────┘│
│                                                       │
│ ┌─ 본문 미리보기 ─────────┐ ┌─ 원본 brief 비교 ─────┐│
│ │ # Claude 4 실무 전략    │ │ - working_title: ...  ││
│ │                         │ │ - angle: ...          ││
│ │ ## 서론                 │ │ - outline:            ││
│ │ Claude 4 시대가 [src-1]│ │   - 서론              ││
│ │ ...                     │ │   - ...               ││
│ └─────────────────────────┘ └───────────────────────┘│
│                                                       │
│ [거절] [수정 요청] [승인 → 발행] [승인 → 예약]       │
└───────────────────────────────────────────────────────┘
```

### 5. `web/src/api/admin.js` 클라이언트

```js
const API_BASE = import.meta.env.VITE_EDITOR_API || 'http://localhost:8080';

export async function listDrafts() { ... }
export async function getDraft(articleId) { ... }
export async function getLint(articleId) { ... }
export async function approveDraft(articleId, options = {}) { ... }
// ...
```

### 6. 승인 플로우

```python
# POST /api/drafts/{article_id}/approve
@app.post("/api/drafts/{article_id}/approve")
def approve(article_id: str, payload: ApprovePayload):
    # 1. editorial_lint 재실행 (최신 상태 확인)
    lint_result = editorial_lint.lint_draft(draft_path)
    if not lint_result["can_publish"]:
        raise HTTPException(400, f"Lint 실패: {lint_result}")

    # 2. ai_disclosure 자동 삽입 (TASK_018)
    html = disclosure_injector.inject_disclosure(html, template="heavy")

    # 3. Ghost publish
    result = ghost_client.create_post(title, html, status="published")

    # 4. Newsletter 발송 (옵션)
    if payload.send_newsletter:
        ghost_client.send_newsletter(result["post_id"])

    # 5. 발행 로그
    log_publish(article_id, result["post_id"], payload.approver)

    return {"post_id": ..., "url": ...}
```

### 7. 실행

```bash
# 터미널 1: API 서버
python scripts/editor_api_server.py --port 8080

# 터미널 2: 웹 개발 서버
cd web && npm run dev

# 브라우저
http://localhost:5173/?admin=1  # /admin/drafts 라우트 자동 열림
```

### 8. App.jsx 통합
```jsx
const isAdmin = new URLSearchParams(window.location.search).has('admin');

if (isAdmin) {
  // admin 라우트 (간단한 클라이언트 사이드 라우팅)
  return <AdminLayout />;
}
```

---

## 완료 조건
- [ ] `scripts/editor_api_server.py` (FastAPI, 8개 엔드포인트)
- [ ] `web/src/pages/admin/DraftListPage.jsx`
- [ ] `web/src/pages/admin/DraftReviewPage.jsx`
- [ ] `web/src/pages/admin/PublishHistoryPage.jsx`
- [ ] `web/src/api/admin.js` 클라이언트
- [ ] `App.jsx`에 `?admin=1` 분기
- [ ] 승인 플로우: editorial_lint 재실행 → disclosure 삽입 → Ghost publish → (옵션) newsletter
- [ ] 127.0.0.1 바인딩 (외부 접근 차단)
- [ ] 스모크 테스트: 가짜 draft → list → review → approve (Ghost mock)
- [ ] `requirements.txt`: fastapi, uvicorn 추가 (이미 TASK_020에 있었으나 취소됨)

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_029 implemented
```

## 주의사항
- FastAPI는 optional 의존성 — `requirements-admin.txt` 분리 고려
- 승인 버튼 클릭 후 **취소 불가** 경고 UI (이미 Ghost published)
- 뉴스레터 발송은 기본 OFF, 체크박스로 명시 선택
- 외부 노출 절대 금지 — 로컬 전용 강조
- Ghost API 키 없으면 승인 시 친절한 에러 (키 설정 안내)
- 모든 승인 액션을 `logs/publish_actions.jsonl`에 기록 (감사 로그)
