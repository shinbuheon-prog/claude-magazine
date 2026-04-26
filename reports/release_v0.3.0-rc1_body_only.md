5월 31일 정식 발행 1호(Issue 1)의 release candidate. v0.2.1 이후 13 commits — Round 2 디제스트 Gate 1 승인·5월 호 4주 로드맵·외부 큐레이션 파이프라인 5계층 설계·Korea Spotlight·Inside Classmethod 7p Sponsored Content 코너·plan_issue 가이드 + 외부 피드백 시작 준비.

## 🎯 하이라이트

### 5월 정식 발행 1호 80p 정확 도달 매핑 확정
- **15 본문 꼭지 + 광고 1 코너 + 구조 8p = 80p 정확** (`reports/plan_issue_2026-05_guide.md`)
- 카테고리 분포: feature 1 / deep_dive 6 / insight 4 / interview 1 / review 3 / sponsored 1
- A 우선순위 10건 즉시 등록 가능 + B 우선순위 6건 PoC 의존 + 폴백 6 옵션 명시
- 4주 로드맵 — 1·2주차 콘텐츠 생산 / 3·4주차 고도화 (`reports/roadmap_2026-05.md`)

### Round 2 디제스트 Gate 1 모두 승인
- **Round 2.B (W3)**: 5 클러스터 → 4 approve + 1 hold. 15 source_id를 `data/source_registry.db`에 등록 (`reports/monthly_digest_2026-04-W3.md`)
- **Round 2.D (W4)**: SNS 자동화 평일 3일(04-22·23·24) 0건 적재 anomaly 감지. 자매 시스템 점검 의뢰 approve (`reports/monthly_digest_2026-04-W4.md`)
- 갭 분석 5월 plan_issue 우선 후보 2건 + W4 신규 1건 backlog 등록 (`docs/backlog.md` "SNS 디제스트 갭 분석" 6건)

### 외부 큐레이션 파이프라인 5계층 신규 SOP
- L1 수집(RSS·소셜·논문 어댑터 7종) → L2 키워드 필터 → L3 Sonnet/Haiku 요약 → L4 Opus 클러스터링 → L5 Gate 1 채택 (`docs/integrations/external_curation_pipeline.md`)
- **X·Threads 자동 크롤링 기각** — ToS 위반 위험 + 법적 신뢰성 보호. 편집자 수동 큐레이션 + baoyu skill 대체
- 외부 OSS 5종 채택 (mckinsey-pptx · ai-daily-digest · python-hacker-news · menshun · tech-digest) + 2종 참고

### Korea Spotlight 코너 (자체 콘텐츠)
- `scripts/curate_classmethodkr_best.py` — Classmethod Korea Tech Blog 월별 베스트 기고 큐레이터 (RSS + 휴리스틱 점수, LLM 호출 0회)
- 4월 시범 큐레이션 — 14건 중 TOP 5 선정 (`reports/classmethodkr_best_2026-04.md`)
- 매월 Review 카테고리 3p 코너 + 블로그 트래픽 유입 효과

### Inside Classmethod 7p Sponsored Content 코너
- 일본본사 Claude 컨설팅 + 한국법인 + Claude 오프라인 밋업 1회차(2025-04-23) + Claude 커뮤니티 안내 통합 7p (`reports/inside_classmethod_2026-05_draft.md`)
- `docs/governance.md` §"Sponsored Content" 6 의무 신규 — AD 배지·footer·시각 분리·광고 비율 ≤10%·식별성·Colophon
- `scripts/plan_issue.py` `sponsored` 카테고리 신규 (1줄 패치)

### 외부 피드백 시작 준비
- README.md §"피드백 환영" 신규 — 6 영역 + 4 경로 (Discussions·Issues·Threads·이메일)
- CONTRIBUTING.md 외부 기여자 7 섹션 신규 (콘텐츠 제안·매거진 정체성·라이선스·Code of Conduct·FAQ)
- GitHub Discussions 활성화 권장 + 4 카테고리 (Ideas·General·Q&A·Show and tell)

### 운영 도구
- `scripts/audit_budget.py` — illustration 월간 예산 감시 CLI. `CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP` 초과 자동 차단
- `pipeline/source_ingester.py` `rights_status` 패스스루 1줄 패치 (자체 콘텐츠 `free` 등록 가능)

## 📦 발행사

**Anthropic 공식 리셀러 클래스메소드 그룹의 한국 법인** (클래스메소드코리아) 발행.
한국어권 Claude 실무자를 위한 무료 발행 매거진. 인간 편집 책임 + Claude AI 보조.

## 🤝 피드백 환영

5/31 정식 발행 전 외부 피드백을 받습니다:

- **GitHub Discussions** — 콘텐츠 주제 제안·운영 모델 토론
- **GitHub Issues** — 버그 리포트·기능 제안
- **이메일** info@classmethod.kr — 협업·기고·Sponsored Content 문의
- 매거진 Threads 게시글 댓글 (수시)

자세한 안내: [README.md §"피드백 환영"](https://github.com/shinbuheon-prog/claude-magazine#피드백-환영-2026-05-정식-발행-1호-준비-중) · [CONTRIBUTING.md](https://github.com/shinbuheon-prog/claude-magazine/blob/main/CONTRIBUTING.md)

## 📋 인프라 검증

- 97/97 pytest pass / ruff lint clean / 전 신규 파일 mojibake clean (UTF-8)
- main 브랜치 v0.2.1 → e66da2a 동기화 완료 (3회 머지)
- CI 7-job 병렬 모두 green

## 🗓 다음 단계

- **5/03 (금)까지**: 외부 피드백 1차 수집 (Threads + GitHub) → 5월 호 plan_issue 반영
- **5/04 (월)**: `plan_issue init --month 2026-05 --theme "..."` 실행, A 우선순위 10건 등록
- **5/05~5/10**: 콘텐츠 생산 1주차 (16 brief 생성)
- **5/11~5/17**: 콘텐츠 생산 2주차 (draft 작성)
- **5/18~5/24**: 고도화 1주차 (factcheck·standards·diversity)
- **5/25~5/31**: 고도화 2주차 + 발행 (시각자산·publish·Ghost·SNS) → **v0.3.0 정식 발행**

전체 변경 내역은 [CHANGELOG.md](https://github.com/shinbuheon-prog/claude-magazine/blob/main/CHANGELOG.md) 참조.

> "AI는 편집자를 대체하지 않습니다. 편집자가 더 많은 것을 더 잘하게 합니다."
