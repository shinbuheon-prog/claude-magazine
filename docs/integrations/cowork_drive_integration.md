# Cowork × Google Drive — 매거진 통합 아키텍처

코리아로컬팀의 SNS運営（Threads）Drive 폴더를 Cowork 커넥터로 매거진 프로젝트에 연결하는 설계.

## 통합 시나리오 (확정)

**시나리오 B — 연계** (Drive 입력 → 매거진 출력)

- Drive 시스템(코리아로컬팀 자체 운영)은 그대로 유지 — 별도 시스템
- 매거진은 Drive 일일 산출물을 콘텐츠 소스로 활용
- Cowork 커넥터가 데이터 흐름의 매개
- 매거진 repo에 자동 commit 금지 — 편집자 승인 후에만 명시 위치로 import

---

## 데이터 흐름

```
[Drive: 코리아로컬팀 SNS運営]
        ↓ (Cowork Drive 커넥터, 일 1회 sync)
[Cowork 프로젝트 컨텍스트에 주입]
        ↓
[Cowork 작업 (Claude)] ─── 사람 편집자 검토 ───┐
        ↓                                      ↓
[Drive 자료 분석 리포트]                 [발행 가능 콘텐츠 후보]
        ↓                                      ↓
[매거진 source_registry 등록 후보]   [매거진 brief/draft/channel_rewriter 입력]
        ↓                                      ↓
[편집자 승인]                          [편집자 승인]
        ↓                                      ↓
[매거진 repo: data/source_registry.db]  [매거진 repo: drafts/, web/public/]
```

**중요**: Cowork → 매거진 repo로의 모든 commit은 **편집자 명시 승인 후 Claude(또는 Codex)가 별도 PR로 진행**. Cowork 자동 commit 금지.

---

## Drive 폴더별 매거진 활용 매핑

### 1. `2026-04-XX/01_cardnews/` (일일 카드뉴스 산출물)

**매거진 활용**:
- channel_rewriter(TASK_023) SNS 카드뉴스 후보로 활용
- card-news-builder skill(TASK_041) 7 layout과 비교해 디자인 다양화 영감
- 큐레이션 후 매거진 월간 이슈의 SNS 채널에 재배포 가능

**Cowork 작업 패턴**:
- 일일 신규 카드뉴스 분석 → 매거진 톤앤매너 정합성 평가
- 출처·인용·AI 고지 점검 (TASK_018·025·045)
- 매거진 채널(Instagram·LinkedIn·Twitter)별 적합도 스코어링

**매거진 측 intake**:
- source_registry 등록 (TASK_004) — 출처·발행처·시효성·라이선스
- 발행 결정은 편집자 (Cowork 자동 발행 금지)

### 2. `2026-04-XX/02_blog/` (일일 블로그 콘텐츠)

**매거진 활용**:
- brief_generator(TASK_003) 입력 소스
- 월간 매거진 80페이지 콘텐츠 큐레이션 풀
- 한국어권 Claude 실무 사례로 매거진 Deep Dive·Feature 섹션 후보

**Cowork 작업 패턴**:
- 신규 블로그 글 분석 → 매거진 카테고리 분류 (feature·deep_dive·interview·review·insight)
- 원문 충실도 검증 (TASK_025) — 번역이 아닌 해설로 재가공 가능 여부
- source_diversity(TASK_019) 4규칙 사전 점검 (언어·관점·발행처·시효성)

**매거진 측 intake**:
- source_ingester(TASK_032) URL 모드(TASK_040)로 등록 후보
- plan_issue.py(TASK_036) 월간 플랜에 후보 기사로 제안

### 3. `_workspace/scripts/` (자매 시스템 자동화 코드)

**매거진 활용**: **참조 전용** (코드 자동 import 금지)

| Drive 스크립트 | 매거진 갭 분석 결과 |
|---|---|
| `fetch_threads_sources.py` | **갭 — Threads 채널 미지원**. 매거진 channel_rewriter는 Instagram·LinkedIn·Twitter만. 향후 Threads 어댑터 추가 검토 |
| `daily_run.py` | **갭 — 일간 모드**. 매거진은 주간(run_weekly_brief)·월간(publish_monthly). 일간 운영 도입 시 참조 |
| `generate_threads_drafts.py` | 매거진 draft_writer(TASK_003)와 유사. Threads 전용 톤 차용 가능 |
| `select_blogs.py`·`select_cards.py` | 매거진 source_diversity·plan_issue 패턴과 동등 |
| 나머지 (`fetch_*`·`generate_*`·`notify_*`) | 매거진 동등 기능 모두 보유 (더 발전된 형태) |

**Cowork 작업 패턴**:
- Drive 코드 변경 감지 → 매거진 갭 분석 리포트 자동 생성
- 신규 패턴 발견 시 docs/backlog.md 후보 항목 제안

### 4. `_workspace/assets/` (브랜드 자산)

**매거진 활용**:
- `classmethod_korea_logo.ai` → 매거진 web/public/ 후보 (소스 자산)
- `logo_dark.png`·`logo_white.png`·`wf_icon.png` → 매거진 다크/라이트 모드 또는 SNS 카드뉴스 푸터

**Cowork 작업 패턴**:
- 신규 자산 등록 시 매거진 import 후보 알림
- 라이선스·저작권 메타데이터 동시 수집

**매거진 측 intake**:
- 편집자 승인 후 `web/public/` 또는 `web/src/assets/`로 import
- 라이선스 정보는 `docs/asset_licenses.md` 신규 등록 (필요 시)

### 5. `_workspace/templates/card.html` (카드 HTML 템플릿)

**매거진 활용**:
- TASK_041 card-news-builder의 7 layout JSON 스키마와 **다른 접근** (HTML 직접 vs 구조화 JSON)
- 두 패턴 비교 후 일부 시각 요소 차용 가능
- 직접 import는 비권장 — 매거진은 React 컴포넌트 기반

**Cowork 작업 패턴**:
- 템플릿 변경 시 매거진 SNS 카드뉴스 7 layout 영향 분석
- 시각 요소 차용 후보 docs/backlog.md 등록 제안

### 6. `2026-04-XX/` 일별 디렉터리 명명 규칙

**매거진과의 동기화**:
- 매거진 reports/improvement_YYYY-MM-DD.md (TASK_027)와 일자 매핑
- 일별 산출물 ↔ 매거진 주간 브리프 후보 ↔ 월간 매거진 콘텐츠 풀

---

## Cowork 작업 권한 경계

### Cowork가 자동으로 할 수 있는 것
- Drive 자료 조회·요약·분류
- 매거진 컨텍스트 기반 분석 리포트 생성
- source_registry 등록 후보 작성
- 매거진 채널 적합도 스코어링
- docs/backlog.md 항목 후보 제안 (실제 commit은 별도)

### Cowork가 절대 자동으로 하지 않는 것
- 매거진 repo에 commit·push (모든 변경은 편집자 승인 후 별도 PR)
- 매거진 발행 (Ghost·뉴스레터·SNS)
- 코드 변경 (Codex 위임 명세 작성은 OK, 실행은 별도)
- 외부 API 호출로 비용 발생 (이미지 생성·유료 LLM 등)
- Drive에 쓰기 (커넥터 권한도 읽기 전용)

---

## 향후 강화 후보 (백로그)

본 통합이 1~2주 운영된 후 검토할 항목:

### 1. source_ingester에 Drive type 추가 (Cowork 매개 없이 직접)
- 현재: Cowork 커넥터가 Drive 데이터를 사람·Claude에게 컨텍스트로 제공
- 향후: source_ingester(TASK_032)에 `type: drive` 추가로 매거진 파이프라인이 Drive 직접 폴링
- 트레이드오프: Drive API 인증 필요 vs Cowork 의존성 제거
- 결정 기준: Cowork 커넥터 비용·안정성·커버리지

### 2. Threads 채널 어댑터 (channel_rewriter 확장)
- 출처: Drive `_workspace/scripts/generate_threads_drafts.py` 패턴
- 매거진 channel_rewriter에 Threads 어댑터 추가
- 매거진 톤(em-dash·Noto Serif KR) 유지하며 Threads 형식 변환

### 3. 일간 운영 모드 (run_daily_brief.py)
- 출처: Drive `daily_run.py` 패턴
- 매거진은 현재 주간(weekly_brief)·월간(publish_monthly)만
- 일간 모드는 SNS 활성도 높일 때 검토 (편집자 부담 증가 vs 도달 빈도)

---

## 운영 모니터링 지표

Cowork 통합 후 추적할 신호 (TASK_048 대시보드에 추가 검토):

| 지표 | 측정 방법 | 임계 |
|---|---|---|
| Drive sync 성공률 | Cowork sync 로그 | 95%↑ |
| Drive→매거진 source_registry 전환율 | 매거진 source_registry 등록 건수 / Drive 신규 항목 | 정성 평가 |
| 매거진 콘텐츠 중 Drive 출처 비율 | 발행 기사의 source_id 중 Drive 비율 | 다양성 균형 (TASK_019 4규칙) |
| Drive 자료 사용 시 인용 충실도 | TASK_045 citations cross-check pass | 80%↑ |
| 편집자 검토 시간 | Cowork 작업 → 매거진 머지 lag | 1주 이내 |

---

## 변경 이력
- 2026-04-25: 초안 작성. 시나리오 B 확정. 향후 강화 후보 3건 백로그 등록.
