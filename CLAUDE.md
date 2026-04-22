# CLAUDE MAGAZINE — Agent OS

## 프로젝트 정의
Claude 생태계를 실무에 활용하는 한국어권 전문가를 위한 지식 매체.
핵심: **인간 편집 책임 위에 Claude가 생산성을 증폭하는 운영체계**.

## 에이전트 역할 분담
```
Claude Code (오케스트레이터)
  ├── 설계·태스크 정의·코드 리뷰
  └── Codex에 TASK_*.md 위임

Codex (서브에이전트 팀)
  ├── TASK 단위 구현
  ├── 구현 완료 시 status → implemented
  └── 테스트 통과 시 Claude Code에 결과 반환
```

## 기술 스택 (구현 시 반드시 참고)
| 영역 | 선택 | 비고 |
|---|---|---|
| LLM | `anthropic` 패키지 (Python) | 스트리밍 필수, request_id 로깅 필수 |
| CMS | Ghost Admin API v4 | JWT 인증 |
| 출처 DB | SQLite (MVP) | `data/source_registry.db` |
| 워크플로우 | n8n | Webhook 기반 |
| 관측 | Langfuse | trace_id ↔ request_id 연결 |
| 환경변수 | `python-dotenv` | `.env` 파일 로드 |

## 모델 배치 규칙 (반드시 준수)
```python
# 기사 브리프·초안 생성
model = "claude-sonnet-4-6"

# 팩트체크·심층 리포트 최종 검토  
model = "claude-opus-4-7"

# SNS 재가공·태깅·분류
model = "claude-haiku-4-5-20251001"
```

## 코딩 규칙
- 모든 `client.messages.stream()` 호출 후 `request_id` 추출 → `logs/` 저장 필수
- 환경변수는 함수 상단에서 `os.environ["KEY"]`로 직접 읽기 (기본값 없음 → 미설정 시 명확한 에러)
- SQLite 연결은 항상 `try/finally` + `conn.close()`
- CLI는 `argparse` 사용, `--dry-run` 옵션 기본 제공
- 테스트는 `if __name__ == "__main__":` 블록에 스모크 테스트 포함

## 폴더 구조 (네비게이션 맵)
```
claude-magazine/
├── CLAUDE.md              ← 이 파일 (에이전트 OS)
├── CODEX_TASKS            ← 태스크 상태 보드
├── codex_workflow.py      ← 보드 관리 CLI
├── requirements.txt
├── .env.example
│
├── tasks/                 ← Codex 위임 명세서
│   ├── TASK_001.md        prerequisites: 없음
│   ├── TASK_002.md        prerequisites: TASK_001
│   ├── TASK_003.md        prerequisites: TASK_001
│   ├── TASK_004.md        prerequisites: TASK_001
│   ├── TASK_005.md        prerequisites: TASK_003, TASK_004
│   ├── TASK_006.md        prerequisites: TASK_002, TASK_003
│   ├── TASK_007.md        prerequisites: TASK_003, TASK_004, TASK_005, TASK_006
│   └── TASK_008.md        prerequisites: TASK_003 (병렬 가능)
│
├── pipeline/              ← Claude API 파이프라인
│   ├── __init__.py
│   ├── brief_generator.py
│   ├── draft_writer.py
│   ├── fact_checker.py
│   ├── channel_rewriter.py
│   └── source_registry.py
│
├── prompts/               ← 고정 프롬프트 템플릿
│   ├── template_A_brief.txt
│   ├── template_B_draft.txt
│   └── template_C_factcheck.txt
│
├── scripts/               ← 운영 진입점 + PDF 생성
│   ├── run_weekly_brief.py
│   ├── run_monthly_report.py
│   ├── generate_pdf.js        ← Puppeteer 월간 PDF 생성 (TASK_010)
│   ├── build_and_pdf.ps1      ← 빌드→PDF 원스톱 PowerShell 스크립트
│   └── package.json           ← puppeteer 의존성
│
├── web/                   ← 매거진 프론트엔드 (TASK_009, TASK_010)
│   ├── index.html
│   ├── package.json           ← Vite + Tailwind + React + Recharts
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.jsx
│       ├── index.css           ← @media print A4 스타일
│       ├── theme.js            ← 디자인 시스템 토큰
│       ├── App.jsx             ← 탭 UI + ?print=1 PDF 모드
│       └── components/
│           ├── CoverPage.jsx
│           ├── ArticlePage.jsx
│           └── InsightPage.jsx
│
├── output/                ← 생성된 PDF (gitignore)
│   └── claude-magazine-YYYY-MM.pdf
│
├── docs/                  ← 편집·법·거버넌스·설계 규정
│   ├── automation_design.md   ← 전체 자동화 파이프라인 설계도 ★
│   ├── editorial_checklist.md
│   ├── source_policy.md
│   └── governance.md
│
├── .claude/               ← Claude Code Skills (TASK_030)
│   └── skills/                 ← 매거진 전용 skill 5종
│       ├── editorial-review/   - 발행 전 10개 체크 자동 실행
│       ├── fact-check-cycle/   - 팩트체크→수정→재검증 루프
│       ├── source-validation/  - 소스 다양성 4규칙
│       ├── publish-gate/       - 통합 발행 게이트
│       └── sns-distribution/   - 4채널 재가공 + 자산 체크
│
├── spec/                  ← 기사 이상 상태 스펙 (TASK_025)
│   ├── article_standards.yml   - 6 카테고리 pass/fail 기준
│   └── README.md
│
├── config/                ← 운영 설정 (TASK_032)
│   └── feeds.yml               - RSS/Atom 피드 구독 목록
│
├── reports/               ← 자율 개선 루프 출력 (TASK_027)
│   └── improvement_YYYY-MM-DD.md
│
├── data/                  ← DB (gitignore)
├── drafts/                ← 생성된 초안 (gitignore)
└── logs/                  ← API 로그 (gitignore)
```

## 워크플로우 커맨드
```bash
# 보드 동기화
python codex_workflow.py sync

# 태스크 상태 업데이트
python codex_workflow.py update TASK_003 implemented

# 전체 상태 확인
python codex_workflow.py list

# 주간 브리프 드라이런
python scripts/run_weekly_brief.py --topic "TOPIC" --dry-run

# 주간 브리프 발행
python scripts/run_weekly_brief.py --topic "TOPIC" --publish

# 팩트체크 단독 실행
python pipeline/fact_checker.py --draft drafts/FILENAME.md

# 월간 PDF 생성 (PowerShell)
.\scripts\build_and_pdf.ps1 -Month 2026-05

# 월간 PDF 생성 (Node 직접)
cd scripts && node generate_pdf.js --month 2026-05
```

## 편집 검수 체크리스트 (게시 전 필수 10개)
1. 핵심 주장마다 source_id 연결
2. 번역·요약이 원문 대체재가 아닌 해설 중심
3. 제목-본문 과장·낚시성 불일치 없음
4. 인용문·수치·사례명이 원문과 일치
5. AI 생성 가상 사례·수치 혼입 없음
6. 인터뷰·익명 제보 비식별화 완료
7. 이미지·표·차트 라이선스 기록 완료
8. AI 사용 고지 문구 검토 완료
9. 정정 책임자·응답 기한(24h) 지정
10. 모든 request_id → logs/ 저장 확인
