# 월간 매거진 발행 워크플로우 매뉴얼

> **목표**: 80페이지 전후의 월간 PDF 매거진 발행 자동화
> **전제**: 무료 발행, Claude 보조, 편집자 최종 책임
> **배포 채널**: Ghost(Web) + PDF + SNS 재가공

---

## 1. 80페이지 볼륨 구성 설계

### 1.1 표준 지면 배분

| 섹션 | 템플릿 | 꼭지 수 | 페이지 | 소계 |
|---|---|---:|---:|---:|
| **표지·목차·편집자의 말** | Cover·TOC·Editorial | 3 | 1+2+1 | 4 |
| **Cover Story** (특집) | FeaturePage | 1 | 14 | 14 |
| **Deep Dive** (심층) | ArticlePage | 6 | 4 | 24 |
| **Insight** (데이터) | InsightPage | 4 | 3 | 12 |
| **Interview** (대담) | InterviewPage | 3 | 5 | 15 |
| **Review** (제품·도구) | ReviewPage | 3 | 3 | 9 |
| **뒷면 정보** (Colophon·광고·뒷표지) | Colophon | 1 | 2 | 2 |
| **총합** | | **21꼭지** | | **80** |

### 1.2 모델 비용 예측 (꼭지당 평균)

| 템플릿 | Sonnet 브리프·초안 | Opus 팩트체크 | Haiku 재가공 | 꼭지당 합계 |
|---|---|---|---|---|
| FeaturePage (14p) | ~$0.80 | ~$0.40 | ~$0.05 | **~$1.25** |
| ArticlePage (4p) | ~$0.20 | ~$0.10 | ~$0.02 | **~$0.32** |
| InsightPage (3p) | ~$0.15 | ~$0.08 | ~$0.02 | **~$0.25** |
| InterviewPage (5p) | ~$0.25 | ~$0.12 | ~$0.02 | **~$0.39** |
| ReviewPage (3p) | ~$0.15 | ~$0.08 | ~$0.02 | **~$0.25** |

**월간 추정 총 API 비용**: **$7~$12** (21꼭지 기준, Batch 할인 미적용)
**개선 루프 + 웹 검색 포함**: **~$15~$20**

---

## 2. 월간 발행 일정 (4주 모델)

```
Week 1: 기획                Week 2: 제작
  ├─ 월간 주제 확정          ├─ 기사 초안 Sonnet 생성
  ├─ 21꼭지 topic 선정       ├─ 팩트체크 Opus 실행
  ├─ 소스 자동 수집 리뷰     ├─ 편집자 1차 검수
  └─ 꼭지별 담당 할당        └─ 판정 DB 기록

Week 3: 검수·디자인          Week 4: 발행
  ├─ 편집자 최종 검수        ├─ 월간 PDF 컴파일
  ├─ 커버·SNS 이미지 제작    ├─ Ghost 뉴스레터 발송
  ├─ editorial_lint 전체 통과├─ SNS 4채널 배포
  └─ 표지·목차 조립          └─ 개선 리포트 생성
```

---

## 3. 주간 상세 절차

### Week 1 — 기획 (1~7일차)

#### Day 1-2: 월간 주제 결정
편집장 수동 결정. 예: `2026-05호 주제 = "에이전트 시대의 실무 전환"`

#### Day 3-4: 소스 자동 수집 리뷰
```bash
# 지난 주간 자동 수집된 피드 확인
python scripts/run_source_ingest.py --since-days 7 --dry-run --json > /tmp/weekly_sources.json

# source_registry에서 주제 관련 소스 검색
python pipeline/source_registry.py list --topic "agent"
```
→ 편집자가 브라우징 후 꼭지별 소스 할당.

#### Day 5-6: 21꼭지 topic 플래닝
`drafts/plan_2026-05.yml` 작성 (수동):
```yaml
issue: 2026-05
theme: "에이전트 시대의 실무 전환"
planned_articles:
  - slug: agent-economics
    category: feature
    title_draft: "AI 에이전트 경제학"
    assignee: editor-A
    source_ids: [src-001, src-002, src-003, src-004]
  - slug: claude-code-review
    category: review
    title_draft: "Claude Code 6개월 사용기"
    assignee: editor-B
    source_ids: [src-010]
  # ... 19개 더
```

#### Day 7: 소스 다양성 사전 검증
```bash
# 꼭지별 소스 다양성 일괄 체크
for slug in $(yq '.planned_articles[].slug' drafts/plan_2026-05.yml); do
    python pipeline/source_diversity.py --article-id "art-$slug" --strict || echo "$slug 부족"
done
```

---

### Week 2 — 제작 (8~14일차)

#### 꼭지별 제작 루프 (꼭지 1건당)

**Step 1**: 브리프 생성 (Sonnet 4.6)
```bash
python scripts/run_weekly_brief.py \
    --topic "AI 에이전트 경제학" \
    --sources /path/to/sources/*.md \
    --dry-run
# → drafts/brief_YYYYMMDD_HHMMSS.json 생성
```

**Step 2**: 섹션별 초안 작성 (Sonnet 4.6)
- `brief.outline`의 각 섹션마다 `draft_writer.py` 호출
- 연속 4~14페이지 기사: 여러 섹션을 순차 생성

**Step 3**: 팩트체크 (Opus 4.7)
```bash
python pipeline/fact_checker.py --draft drafts/draft_art-agent-economics.md --article-id art-agent-economics
```

**Step 4**: 편집자 1차 검수 + 판정 기록
```bash
# 편집자가 draft 수정 후 판정 DB에 기록
python pipeline/editor_corrections.py add \
    --article-id art-agent-economics \
    --category feature \
    --type {exaggeration|factual|tone|style|structure|clarity} \
    --original "..." --corrected "..." --severity medium
```

#### 21꼭지 병렬 제작
```bash
# 편집자 3명이 7꼭지씩 담당 병렬 진행
# 각자 workflow 반복
```

---

### Week 3 — 검수·디자인 (15~21일차)

#### Day 15-17: editorial_lint 전체 게이트

꼭지별 발행 준비 검증:
```bash
for article in drafts/draft_art-*.md; do
    python pipeline/editorial_lint.py --draft "$article" --strict || echo "실패: $article"
done
```

실패 시 `editorial-review` skill 활용 (자연어로 Claude Code에 요청).

#### Day 18: 종합 품질 게이트
```bash
# 각 꼭지마다 publish-gate skill 트리거
# 또는 직접 실행:
for slug in $(yq '.planned_articles[].slug' drafts/plan_2026-05.yml); do
    python pipeline/editorial_lint.py --draft "drafts/draft_art-$slug.md" --strict
    python pipeline/standards_checker.py --draft "drafts/draft_art-$slug.md" --category "$category"
    python pipeline/source_diversity.py --article-id "art-$slug" --strict
    python pipeline/disclosure_injector.py --html "..." --template "$(category_to_template $category)"
done
```

#### Day 19-20: 시각 자산 제작 (Claude Design)

| 자산 | 수량 | 도구 |
|---|---|---|
| 월간 커버 | 1장 | Claude Design → `web/public/covers/2026-05.png` |
| Cover Story 일러스트 | 2~3장 | Claude Design → `web/public/features/2026-05/` |
| InsightPage 차트 | 4개 (자체 Recharts) | 자동 |
| SNS 카드뉴스 | 꼭지당 3장 = 63장 | Claude Design → `web/public/sns/2026-05/` |
| Interview 포트레이트 | 3장 | 인물 제공 사진 + Claude Design 보조 |

검증:
```bash
python scripts/check_covers.py --month 2026-05
python scripts/check_sns_assets.py --month 2026-05
```

#### Day 21: 표지·목차·편집자의 말 조립

**현재 부족한 컴포넌트** (향후 TASK 후보):
- TOCPage.jsx (목차)
- EditorialPage.jsx (편집자의 말)
- ColophonPage.jsx (뒷면 정보)
- RunningHeader.jsx (페이지 번호·러닝 헤더)

임시 해결책: 수동 페이지 삽입 (LaTeX 또는 pdf-lib로 merge).

---

### Week 4 — 발행 (22~28일차)

#### Day 22: 웹 동시 발행 (Ghost)
```bash
# 각 꼭지를 Ghost에 draft로 업로드 (이미 publish-gate 통과)
for slug in $(yq '.planned_articles[].slug' drafts/plan_2026-05.yml); do
    # ghost_client.create_post() 호출 — 개별 기사
done
# 편집자 승인 UI에서 일괄 published 전환
python scripts/editor_api_server.py --port 8080 &
# → http://localhost:5173/?admin=1 에서 승인
```

#### Day 23: 월간 PDF 컴파일

현재 구조 (6개 페이지): `pdf-compile` skill로 원스톱.

80페이지 확장 버전 (향후 TASK):
```bash
# 1. 각 꼭지를 개별 React 렌더 → PDF
# 2. pdf-lib으로 모든 꼭지 PDF 병합
# 3. 표지·목차·편집자의 말·뒷표지 삽입
python scripts/compile_monthly_pdf.py --month 2026-05 --articles drafts/
# → output/claude-magazine-2026-05.pdf (80페이지)
```

#### Day 24: 뉴스레터 발송
```bash
# Ghost Members API로 구독자에게 일괄 발송
python pipeline/ghost_client.py send-newsletter --issue 2026-05
```

#### Day 25-26: SNS 4채널 배포
```bash
# 21꼭지 × 4채널 = 84개 포스트 (자동 재가공)
for slug in $(yq '.planned_articles[].slug' drafts/plan_2026-05.yml); do
    python pipeline/channel_rewriter.py --draft "drafts/draft_art-$slug.md" --channel sns --post-slug "$slug" --month 2026-05
    python pipeline/channel_rewriter.py --draft "drafts/draft_art-$slug.md" --channel linkedin --post-slug "$slug" --month 2026-05
    python pipeline/channel_rewriter.py --draft "drafts/draft_art-$slug.md" --channel twitter --post-slug "$slug" --month 2026-05
    python pipeline/channel_rewriter.py --draft "drafts/draft_art-$slug.md" --channel instagram --post-slug "$slug" --month 2026-05
done
# 또는 sns-distribution skill 활용
```

편집자는 각 채널 포스트를 수동으로 게시 (자동 게시는 별도 API 연동 필요).

#### Day 27: 개선 리포트 (주간 Cron이 자동 실행됨)
```bash
# 이미 일요일 23:00에 weekly_improvement가 리포트 생성
# reports/improvement_2026-05-XX.md 확인 후 다음 호 피드백
```

#### Day 28: 아카이브·정리
```bash
# PDF를 Cloudflare R2에 업로드 (또는 GitHub Release)
# drafts/ 정리 (archive/ 이동)
mkdir -p archive/2026-05/
mv drafts/draft_art-* archive/2026-05/
mv drafts/brief_* archive/2026-05/
```

---

## 4. 꼭지 제작 플로우 다이어그램

```
[소스 자동 수집 (매일 05:00)]
         ↓
[편집자 주제·꼭지 선정 (Week 1)]
         ↓
[source_diversity 검증]
         ↓
 ┌───────┴───────┐
 │   brief_generator (Sonnet)
 │       ↓
 │   draft_writer (Sonnet, 섹션 반복)
 │       ↓
 │   fact_checker (Opus)
 │       ↓
 │   editor_corrections (편집자 판정 기록)
 │       ↓
 │   editorial_lint (10체크)
 │       ↓
 │   standards_checker (카테고리 기준)
 │       ↓
 │   disclosure_injector (AI 고지 삽입)
 │       ↓
 └───────┬───────┘
         ↓
[통합 PDF 컴파일 (Week 4)]
         ↓
[Ghost 발행 + 뉴스레터]
         ↓
[SNS 4채널 재가공 배포]
         ↓
[weekly_improvement (자율 개선 루프)]
         ↑
         └── (다음 호 피드백)
```

---

## 5. 카테고리별 제작 가이드

### 5.1 Feature (Cover Story, 14페이지)

**구성**:
- 섹션 1: 리드 (왜 지금) — 2p
- 섹션 2-4: 주요 논점 3개 — 각 3p
- 섹션 5: 결론·전망 — 3p

**소스 요구**: 15~20개, 한국어 공식 5+ 영문 공식 5+ 반대 관점 2+

**제작 순서**:
1. brief_generator로 outline 1회
2. draft_writer로 5개 섹션 개별 생성
3. fact_checker 전체 실행
4. 각 섹션 FeaturePage 데이터로 변환
5. pull quote 4개 선정

---

### 5.2 Deep Dive (ArticlePage, 4페이지)

**구성**:
- 정보 테이블 (모델 스펙·가격·비교)
- 인용구 + 본문
- 바차트 (활용 분포·시장 점유율 등)
- 3~4개 포인트

**소스 요구**: 5~8개

**제작**: 표준 파이프라인 1회 완주

---

### 5.3 Insight (3페이지)

**구성**:
- 데이터 차트 (Recharts LineChart·BarChart·AreaChart)
- 주요 지표 2개 (stat blocks)
- Editor Tip 박스

**소스 요구**: 3~5개 (통계 출처 필수)

**주의**: 차트 데이터는 JSON으로 `InsightPage`에 주입. 원본 수치는 source_registry에 반드시 등록.

---

### 5.4 Interview (5페이지)

**구성**:
- 인물 소개 + 핵심 인용문 (1p)
- Q&A 5~8쌍 (4p)

**소스 요구**: 인터뷰 녹취 1개 + 참고 배경 자료 2~3개

**주의**:
- 인터뷰 녹취는 **pii_masker.py로 먼저 마스킹**한 후 Claude에 전달
- Haiku 4.5로 초벌 정리 → Sonnet으로 본문 다듬기
- 인용문 정확도 검증은 fact_checker가 아닌 **원본 녹취와 직접 대조**

---

### 5.5 Review (3페이지)

**구성**:
- 제품명 + 종합점수 + verdict 배지
- 평가 기준 바차트 (3~5개 항목)
- Pros·Cons 2컬럼
- 경쟁 제품 비교표

**소스 요구**: 공식 문서 2+ 경쟁 제품 자료 1+ 사용자 리뷰 1+

---

## 6. 현재 부족한 부분 — 향후 TASK 후보

### TASK_033 (후보): 80페이지 매거진 PDF 컴파일러
현재 `scripts/generate_pdf.js`는 6페이지만 처리. 80페이지 확장 필요.

**구현 내용**:
- 꼭지별 개별 PDF 생성
- `pdf-lib`으로 전체 병합
- 페이지 번호 자동 삽입
- 표지·목차 자동 생성
- 러닝 헤더 (섹션명·페이지 번호)

### TASK_034 (후보): 매거진 추가 컴포넌트
- `TOCPage.jsx` — 목차
- `EditorialPage.jsx` — 편집자의 말
- `ColophonPage.jsx` — 뒷면 정보
- `AdSlotPage.jsx` — 광고 영역 (무료 매거진에서도 파트너 크레딧 등)

### TASK_035 (후보): 월간 플랜 관리 CLI
`scripts/plan_issue.py`:
```bash
python scripts/plan_issue.py init --month 2026-05 --theme "에이전트 시대"
python scripts/plan_issue.py add-article --slug X --category feature
python scripts/plan_issue.py status   # 21꼭지 진행 현황
```

### TASK_036 (후보): 월간 발행 원스톱 스크립트
```bash
python scripts/publish_monthly.py --month 2026-05 --all
# → PDF 컴파일 + Ghost 일괄 발행 + 뉴스레터 + SNS 전부
```

### TASK_037 (후보): 편집자 대시보드 확장
`DashboardPage.jsx`에 월간 진행률 추가:
- 21꼭지 중 N개 완료
- 각 섹션별 publish-gate 통과율
- 남은 작업 체크리스트

---

## 7. 도구·명령어 레퍼런스 (치트시트)

### 매일 실행
```bash
python scripts/run_source_ingest.py          # 피드 자동 수집 (n8n Cron)
```

### 꼭지 제작
```bash
python scripts/run_weekly_brief.py --topic "..." --sources ...
python pipeline/fact_checker.py --draft ... --article-id ...
python pipeline/editorial_lint.py --draft ... --strict
python pipeline/standards_checker.py --draft ... --category ...
python pipeline/source_diversity.py --article-id ... --strict
python pipeline/disclosure_injector.py --html ... --template ...
```

### 편집자 판정 기록
```bash
python pipeline/editor_corrections.py add ...
```

### 자산 검증
```bash
python scripts/check_covers.py --month 2026-05
python scripts/check_sns_assets.py --month 2026-05
python scripts/validate_skills.py --strict
python scripts/check_env.py --strict
```

### 발행
```bash
python scripts/editor_api_server.py --port 8080   # 승인 UI 서버
node scripts/generate_pdf.js --month 2026-05      # PDF 생성 (현재 6p)
```

### 관측·개선
```bash
python scripts/export_metrics.py --since-days 30 --format md
python scripts/weekly_improvement.py              # 주간 개선 제안
```

### Claude Code Skills (자연어 트리거)
- "기사 검토해줘" → editorial-review
- "팩트체크 루프 돌려줘" → fact-check-cycle
- "소스 다양성 확인" → source-validation
- "발행 준비해줘" → publish-gate
- "SNS 재가공해줘" → sns-distribution
- "이번 주 브리프 만들어줘" → brief-generation
- "월간 PDF 뽑아줘" → pdf-compile
- "주간 개선 분석" → weekly-improvement

---

## 8. 월간 KPI 체크리스트

매월 마지막 날 확인:

### 볼륨·발행
- [ ] 80±5 페이지 PDF 완성
- [ ] 21꼭지 전체 Ghost 발행
- [ ] 뉴스레터 발송 완료
- [ ] SNS 4채널 배포 완료

### 품질
- [ ] editorial_lint 10체크 **전 꼭지 통과**
- [ ] standards_checker 카테고리별 must_pass 100%
- [ ] source_diversity 4규칙 90% 이상 통과
- [ ] 편집자 판정 `severity: high` 5건 이하

### 비용·관측
- [ ] 총 API 비용 < $25
- [ ] AI:인간 시간 비율 측정 (metrics_collector)
- [ ] 모든 request_id logs/ 저장 확인

### 법·거버넌스
- [ ] 전 꼭지 AI 사용 고지 삽입
- [ ] PII 스크러빙 (인터뷰 녹취 등)
- [ ] 이미지 라이선스 licenses.json 등록
- [ ] 정정 책임자·24시간 기한 고지

---

## 9. 자주 발생하는 실수와 대응

| 실수 | 원인 | 대응 |
|---|---|---|
| 꼭지 페이지 수 초과 | Sonnet이 outline 길게 잡음 | brief_generator에 `max_sections: 5` 제약 |
| 인용문 원문 불일치 | 편집 중 Claude가 변형 | pii_masker 패턴 차용해 인용문 토큰화 후 복원 |
| 팩트체크 "수정 필요" 과다 | 소스 다양성 부족 | source_diversity 사전 실행 |
| SNS 자산 누락 | Claude Design 수동 작업 놓침 | Week 3 Day 19~20 고정 일정화 |
| editorial_lint 반복 실패 | 판정 DB 미반영 | editor_corrections 즉시 기록 습관화 |
| PDF 페이지 깨짐 | A4 마진 계산 오류 | `.print-page` CSS 확인 |

---

## 10. 예상 운영 리듬 (정착 단계)

**초기 3개월** (2026-05 ~ 2026-07):
- 편집자 1명 + Claude 보조
- 꼭지당 6~10시간 (편집 시간)
- 월 120~160시간 작업

**안정화 6개월 후**:
- 편집자 1명 + Claude 보조
- 꼭지당 3~5시간 (판정 DB 축적 효과)
- 월 60~90시간 작업
- **AI:인간 시간 비율 1:2 → 1:0.5 목표**

**1년 후** (자율 개선 루프 누적):
- 패턴 SOP 50+ 축적
- 신규 편집자 온보딩 1일 이내
- 편집자 1명으로 월 80p 매거진 유지 가능

---

## 관련 문서

- [CLAUDE.md](../CLAUDE.md) — 프로젝트 전체 가이드
- [AGENTS.md](../AGENTS.md) — 에이전트 행동 규칙
- [automation_design.md](automation_design.md) — 전체 자동화 파이프라인 설계도
- [worktree_example/README.md](worktree_example/README.md) — 병렬 작업 가이드
- [superpowers_integration.md](superpowers_integration.md) — Claude Code Skills 통합
