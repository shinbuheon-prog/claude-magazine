# Claude Magazine — 자동화 파이프라인 설계도

> 최종 업데이트: 2026-04-21

---

## 전체 흐름 (End-to-End)

```
[소스 수집]          [콘텐츠 생성]         [검수]           [발행]            [PDF 아카이브]
     │                    │                  │                │                   │
n8n Cron             Claude Sonnet       편집자 승인       Ghost CMS         Puppeteer
(매주 월 09:00)  →   브리프·초안 생성  →  Webhook 수신  →  포스트 발행   →  월간 PDF 생성
                     Claude Opus         (수동 검토)       뉴스레터 발송     output/*.pdf
                     팩트체크
                     Claude Haiku
                     SNS 재가공
```

---

## 레이어별 상세

### 1. 소스 수집 (n8n — TASK_007)
| 항목 | 내용 |
|---|---|
| 트리거 | 매주 월요일 09:00 KST (Cron) |
| 동작 | 소스 URL 목록 fetch → `run_weekly_brief.py --dry-run` 실행 |
| 알림 | Slack Webhook ("브리프 생성 완료, Ghost 확인 후 발행") |
| 실패 처리 | 15분 간격 3회 재시도 → 실패 시 Slack 에러 알림 |
| 파일 | `n8n/workflow_1_scheduler.json` |

### 2. 콘텐츠 생성 파이프라인 (Python — TASK_003~005)
```
pipeline/
├── brief_generator.py    ← Sonnet 4.6: 기사 브리프·초안 (빠른 생성)
├── draft_writer.py       ← Sonnet 4.6: 본문 초안 작성
├── fact_checker.py       ← Opus 4.7:  팩트체크·심층 검토 (정확도 최우선)
├── channel_rewriter.py   ← Haiku 4.5: SNS/LinkedIn 재가공 (고속·저비용)
└── source_registry.py    ← SQLite: 출처 등록·조회 (TASK_004)
```

**모델 배치 원칙**
| 작업 | 모델 | 이유 |
|---|---|---|
| 브리프·초안 | `claude-sonnet-4-6` | 비용·속도 균형, Batch 50% 할인 |
| 팩트체크·검토 | `claude-opus-4-7` | 최고 정확도 필요 |
| SNS 재가공·분류 | `claude-haiku-4-5-20251001` | 고속·최저비용 |

### 3. 편집자 승인 (수동 → n8n — TASK_007)
```
편집자가 Ghost 초안 확인
  → 승인 시: POST /webhook/publish-approved
  → n8n workflow_2_publish.json 수신
  → run_weekly_brief.py --publish 실행
  → Ghost 포스트 라이브 + 뉴스레터 발송 (TASK_006)
```

### 4. SNS 재가공 자동화 (n8n — TASK_007)
```
Ghost post.published 이벤트
  → n8n workflow_3_sns.json 수신
  → channel_rewriter.py --channel sns
  → channel_rewriter.py --channel linkedin
  → Slack 알림 ("SNS 초안 생성 완료, 검토 후 게시하세요")
```

### 5. 관측·로깅 (Langfuse — TASK_008)
- 모든 Claude API 호출: `request_id` 추출 → `logs/` 저장
- Langfuse trace_id ↔ request_id 연결
- 비용·지연·품질 대시보드 연동

### 6. 월간 PDF 생성 (Puppeteer — TASK_010 ✅ 완료)
```
매월 말 수동 실행 (추후 n8n Cron 연동 가능)

scripts/build_and_pdf.ps1
  ① web/ → npm run build (Vite 빌드)
  ② scripts/ → node generate_pdf.js
       - Node HTTP 서버: dist/ 서빙 (port 4173)
       - Puppeteer headless: /?print=1 접근
       - App.jsx 전체 페이지 A4 렌더링
         (CoverPage → ArticlePage → InsightPage)
       - page.pdf({ format: 'A4', printBackground: true })
       - 저장: output/claude-magazine-YYYY-MM.pdf
```

---

## 태스크 의존성 맵

```
TASK_001 (초기 설정)
  ├── TASK_002 (Ghost CMS)
  │     └── TASK_006 (뉴스레터 발행)
  ├── TASK_003 (브리프 파이프라인)
  │     ├── TASK_005 (팩트체크)
  │     └── TASK_008 (Langfuse)
  ├── TASK_004 (출처 레지스트리)
  └── TASK_009 (웹 레이아웃) ✅
        └── TASK_010 (PDF 생성) ✅

TASK_007 (n8n 자동화)  ← prerequisites: TASK_003, TASK_004, TASK_005, TASK_006
```

---

## 진행 현황

| 태스크 | 제목 | 상태 |
|---|---|---|
| TASK_001 | 프로젝트 초기 설정 | 🔲 todo |
| TASK_002 | Ghost CMS 세팅 | 🔲 todo |
| TASK_003 | Claude API 브리프 파이프라인 | 🔲 todo |
| TASK_004 | 출처 레지스트리 (SQLite) | 🔲 todo |
| TASK_005 | 팩트체크 에이전트 | 🔲 todo |
| TASK_006 | 뉴스레터 발행 | 🔲 todo |
| TASK_007 | n8n 워크플로우 자동화 | 🔲 todo |
| TASK_008 | Langfuse 관측 연동 | 🔲 todo |
| TASK_009 | 웹 레이아웃 컴포넌트 | ✅ merged |
| TASK_010 | 월간 PDF 생성 파이프라인 | ✅ merged |

---

## 다음 우선순위 (권장 순서)

1. **TASK_001** — `.env`, `data/`, `drafts/`, `logs/` 초기화 (모든 태스크의 전제)
2. **TASK_003** — Claude API 브리프 파이프라인 (핵심 콘텐츠 엔진)
3. **TASK_004** — 출처 레지스트리 (TASK_003과 병렬 가능)
4. **TASK_002** — Ghost CMS 세팅
5. **TASK_005** — 팩트체크 에이전트
6. **TASK_006** — 뉴스레터 발행
7. **TASK_007** — n8n 워크플로우 자동화
8. **TASK_008** — Langfuse 관측 연동

---

## 월간 발행 체크리스트

```
[ ] TASK_003: 이번 달 주제 브리프 생성 (Sonnet)
[ ] TASK_005: 팩트체크 통과 (Opus)
[ ] 편집자 최종 검수 10개 항목 확인 (editorial_checklist.md)
[ ] TASK_006: Ghost 발행 + 뉴스레터 발송
[ ] TASK_010: PDF 생성 → output/claude-magazine-YYYY-MM.pdf
[ ] Git 커밋 및 GitHub push
```
