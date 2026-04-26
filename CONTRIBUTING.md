# 기여 가이드 (Contributing)

Claude Magazine은 **Anthropic 공식 리셀러 클래스메소드 그룹의 한국 법인(클래스메소드코리아)**이 운영하는 한국어권 Claude 실무자용 무료 발행 매거진입니다. 외부 기여를 환영합니다.

> **현재 상태 (2026-04-26)**: v0.2.1 closure 완료, 2026-05-31 정식 발행 1호(Issue 1) 준비 중. 외부 피드백을 5월 호 콘텐츠와 운영 방식에 반영합니다.

---

## 외부 기여자 안내

### 1. 기여 종류와 경로

| 기여 종류 | 권장 경로 | 진입 장벽 | 처리 시간 |
|---|---|---|---|
| **콘텐츠 주제 제안** | GitHub Discussions ("Ideas" 카테고리) | GitHub 계정 | 7일 내 응답 |
| **운영 모델 토론** | GitHub Discussions ("General" 카테고리) | GitHub 계정 | 7일 내 응답 |
| **버그 리포트** | GitHub Issues (`bug_report` 템플릿) | GitHub 계정 | 7일 내 분류 |
| **기능 제안** | GitHub Issues (`feature_request` 템플릿) | GitHub 계정 | 14일 내 분류 |
| **코드 기여 (PR)** | GitHub Pull Request | GitHub 계정 + 개발 환경 | 14일 내 1차 리뷰 |
| **콘텐츠 제공 (인터뷰·기고)** | 이메일 info@classmethod.kr | 없음 | 7일 내 응답 |
| **Sponsored Content 협업** | 이메일 info@classmethod.kr | 없음 | 7일 내 응답 |
| **간단 의견·질문** | 매거진 Threads 게시글 댓글 | Threads 계정 | 비정기 응답 |

### 2. 콘텐츠 주제 제안 — 가장 환영하는 기여

매거진은 한국어권 Claude 실무자에게 도움이 되는 콘텐츠를 우선 채택합니다.

**좋은 주제 제안의 요소**:
- **구체적 운영 시나리오** — "Claude Code로 X를 자동화한 사례" / "Bedrock에서 Y 트러블슈팅 경험"
- **외부 cross-check 가능 source** — Anthropic 공식 docs / AWS 공식 docs / 논문 / 본인 블로그·GitHub
- **매거진 카테고리 적합성** — Cover Story / Deep Dive / Insight / Interview / Review 중 어디
- **목표 페이지 분량** — 1~14p (카테고리별 표준은 [docs/monthly_magazine_workflow.md](docs/monthly_magazine_workflow.md) §1.1)
- **예상 독자** — 비엔지니어·엔지니어·관리자 중 누구

**채택 흐름**:
1. GitHub Discussions에 주제 제안 → 편집장 1차 검토 (7일 내)
2. 채택 가능성 있으면 다음 호 backlog 등록 ([docs/backlog.md](docs/backlog.md))
3. plan_issue 시점에 정식 plan 추가 (월말~익월 초)
4. brief → draft → factcheck → editorial_lint → publish-gate
5. 발행 후 GitHub Discussion에서 알림

### 3. 매거진 정체성·정책 (기여 전 필독)

| 항목 | 정책 |
|---|---|
| **무료 발행** | 결제·유료 구독 시스템 제안 금지 (TASK_020 cancelled) |
| **인간 편집 책임** | AI는 보조, 모든 발행 결정은 편집장 |
| **모델 배치 규칙** | brief·draft = Sonnet 4.6 / factcheck = Opus 4.7 / SNS 재가공 = Haiku 4.5 ([CLAUDE.md](CLAUDE.md)) |
| **외부 자동 크롤링** | X·Threads 자동 크롤링 기각 (ToS 위반 위험). 편집자 수동 큐레이션 + baoyu skill 사용 ([docs/integrations/external_curation_pipeline.md](docs/integrations/external_curation_pipeline.md) §2-2) |
| **Sponsored Content** | 발행사·관계사 서비스 소개 코너 게재 가능. 매호 광고 비율 ≤10% + 6 표기 의무 ([docs/governance.md](docs/governance.md) §"Sponsored Content") |
| **Korean 인코딩** | UTF-8 강제, mojibake 검증 필수 |

### 4. 라이선스·개인정보

- 매거진 발행 콘텐츠는 매거진 자체 라이선스 정책 (현재 Internal). 인용 한도: 200자 + source 표기 ([docs/source_policy.md](docs/source_policy.md))
- 코드 기여 = 본인 기여를 매거진 라이선스에 따라 사용함을 동의
- AI 사용 고지: 모든 본문 하단에 1줄 고지 ([docs/governance.md](docs/governance.md))
- 개인정보: GitHub 정보는 GitHub 정책 / 이메일·인터뷰는 30일 내 삭제·비식별화

### 5. Code of Conduct

- 다른 기여자 존중·건설적 비평
- 한국어/영어 자유 사용 (한국어 우선 매체)
- 금지: 개인 공격·차별·spam·매거진 정체성 흐리는 PR (유료 구독 제안·ToS 위반 도구 권유 등)
- 위반 보고: info@classmethod.kr 또는 GitHub Issues 비공개 라벨 → 7일 내 조치

### 6. 자주 묻는 질문 (FAQ)

**Q1. 매거진은 유료인가요?** A. **무료**. 결제 시스템 도입 계획 없음.
**Q2. 광고는?** A. Sponsored Content 코너 매호 ≤10% 게재 가능 ([docs/governance.md](docs/governance.md)).
**Q3. AI가 모든 콘텐츠를 작성하나요?** A. **아니요**. 인간 편집장이 brief·draft·factcheck·publish-gate 모두 명시 승인.
**Q4. 기고 보상이 있나요?** A. 현재 무료 기고만 받음 (단 매거진 본문에 source_id + 블로그 링크 노출 → 트래픽 유입). 향후 유료 모델은 별도 결정.

### 7. 연락처

| 용도 | 채널 |
|---|---|
| GitHub Discussions | https://github.com/shinbuheon-prog/claude-magazine/discussions |
| GitHub Issues | https://github.com/shinbuheon-prog/claude-magazine/issues |
| 이메일 (편집·기고·협업·Sponsored) | info@classmethod.kr |
| 매거진 Threads (편집장 본인 게시) | https://www.threads.com/@s.zzangpapa/post/DXlMyXzEqnf |
| 매거진 Threads (운영진 리포스트) | 박동현 운영진 계정 (한일 커뮤니티) |
| 발행사 (클래스메소드코리아) | https://classmethod.jp / 050-1754-1651 |

---

# 내부 팀 협업 가이드

> 본 섹션은 매거진 운영 팀 내부용입니다. 외부 기여자는 위 §"외부 기여자 안내"를 참조하세요.

## 브랜치 전략

```
main          ← 배포 가능한 안정 코드 (직접 push 금지)
  └── develop ← 통합 브랜치 (PR 머지 대상)
        ├── task/TASK_001   ← Codex 태스크별 브랜치
        ├── task/TASK_003
        └── article/2026-05-01-claude-sonnet-guide  ← 기사별 브랜치
```

## 작업 시작

```bash
# 최신 develop 기준으로 브랜치 생성
git checkout develop
git pull origin develop
git checkout -b task/TASK_003

# 작업 완료 후
git add .
git commit -m "feat(TASK_003): brief_generator.py 구현"
git push origin task/TASK_003
```

## 커밋 메시지 규칙

```
feat(범위): 새 기능 추가
fix(범위): 버그 수정
chore(범위): 설정·의존성 변경
docs(범위): 문서 수정
style(범위): 포맷·린트만 수정
test(범위): 테스트 추가·수정

예시:
feat(TASK_003): brief_generator.py 스트리밍 구현
fix(source_registry): mark_used 중복 방지 버그 수정
docs(TASK_005): 팩트체크 에이전트 완료 조건 명확화
```

## PR 규칙

1. **PR 대상**: `develop` 브랜치 (main 직접 PR 금지)
2. **PR 템플릿** 체크리스트 전부 완료 후 요청
3. **리뷰어**: 편집장 1인 필수 승인
4. **CI 통과** 필수 (lint + 스모크 테스트)

## Codex 태스크 위임 워크플로우

```
1. GitHub Issue 생성 (ISSUE_TEMPLATE/task.md 사용)
2. 브랜치 생성: git checkout -b task/TASK_XXX
3. tasks/TASK_XXX.md 를 Codex에 전달
4. Codex 구현 완료 → python codex_workflow.py update TASK_XXX implemented
5. PR 생성 → develop 머지
6. python codex_workflow.py update TASK_XXX merged
```

## 기사 작업 워크플로우

```
1. GitHub Issue 생성 (ISSUE_TEMPLATE/article.md 사용)
2. 브랜치 생성: git checkout -b article/YYYY-MM-DD-slug
3. pipeline 실행:
   python scripts/run_weekly_brief.py --topic "TOPIC" --dry-run
4. drafts/ 확인 → 편집자 검수
5. 편집 검수 체크리스트 10개 항목 완료
6. PR 생성 → develop 머지 → 발행
```

## 환경 설정

```bash
# 1. 레포 클론
git clone https://github.com/shinbuheon-prog/claude-magazine.git
cd claude-magazine

# 2. 환경변수 설정
cp .env.example .env
# .env 편집: ANTHROPIC_API_KEY 등 입력

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 보드 확인
python codex_workflow.py list
```

## 민감정보 규칙

- `.env` 는 절대 커밋 금지 (`.gitignore`에 포함됨)
- API 키는 팀 내 안전한 채널(1Password, Slack DM 등)로만 공유
- `logs/`, `data/`, `drafts/` 는 gitignore 대상 (개인 로컬에만)
