# TASK_030 — 매거진 전용 Claude Code Skills 정의

## 메타
- **status**: todo
- **prerequisites**: TASK_016, TASK_025, TASK_026
- **예상 소요**: 60분
- **서브에이전트 분할**: 불필요
- **Phase**: 5 (Superpowers 철학 적용)

---

## 목적
obra/superpowers 원칙 적용: **Skill 기반 모듈화 + Verify before success**.
기존 `pipeline/` 모듈을 Claude Code가 자동 호출 가능한 **Skills**로 등록해, 편집자가 자연어 요청만으로 복잡한 파이프라인을 실행할 수 있게 한다.

리포트 인용: _"Skills 자동 트리거 + 서브에이전트 분산 + 증거 기반 검증. Systematic over ad-hoc—Process over guessing."_

---

## 구현 명세

### 1. 생성 폴더 구조
```
.claude/
└── skills/
    ├── editorial-review/SKILL.md       ← 발행 전 10개 체크 자동 실행
    ├── fact-check-cycle/SKILL.md       ← 팩트체크 → 수정 → 재검증 루프
    ├── source-validation/SKILL.md      ← 소스 다양성 4규칙 검증
    ├── publish-gate/SKILL.md           ← editorial_lint + standards_checker 통합 게이트
    └── sns-distribution/SKILL.md       ← 채널별 재가공 + 자산 체크
```

### 2. SKILL.md 공통 포맷

```yaml
---
name: {skill-name}
description: {한 문장, 자동 트리거 키워드 포함}
allowed-tools: Bash, Read, Edit, Grep
---

# {Skill 이름}

## 언제 사용
- {트리거 조건 1}
- {트리거 조건 2}

## 절차 (Systematic)
1. {단계 1 + 실행 명령어}
2. {단계 2}
...

## Verify before success
- [ ] {검증 기준 1}
- [ ] {검증 기준 2}
```

### 3. 5개 Skill 상세 정의

#### A. editorial-review
- **트리거**: "기사 검토", "editorial review", draft 파일 경로 언급
- **절차**: `editorial_lint.py` 실행 → 10개 체크 결과 요약 → 실패 항목별 수정 제안
- **Verify**: `can_publish: True` 확인

#### B. fact-check-cycle
- **트리거**: "팩트체크 루프", "fact check cycle"
- **절차**: `fact_checker.py` 실행 → "수정 필요" 문장 추출 → `draft_writer.py`로 재작성 → 재팩트체크 (최대 2회 반복)
- **Verify**: 전체 위험도 "낮음" 또는 "중간"

#### C. source-validation
- **트리거**: "소스 다양성", "source validation", article_id 언급
- **절차**: `source_diversity.py --article-id X --strict` 실행
- **Verify**: 4개 규칙 모두 통과 또는 사용자 예외 승인

#### D. publish-gate
- **트리거**: "발행 준비", "publish gate", "게시 전 검증"
- **절차**: 
  1. `editorial_lint.py --strict`
  2. `standards_checker.py --category X`
  3. `source_diversity.py --article-id X`
  4. `disclosure_injector.py` (AI 고지 삽입)
  5. 모두 통과 시 Ghost draft 상태 확인 메시지
- **Verify**: 3단계 모두 통과 + disclosure 삽입 완료

#### E. sns-distribution
- **트리거**: "SNS 재가공", "sns distribution", "카드뉴스"
- **절차**: 
  1. `channel_rewriter.py --channel sns --post-slug X --assets-report`
  2. 자산 누락 시 `claude.ai/design` 링크 안내
  3. linkedin/twitter 채널도 순차 실행
- **Verify**: 기대 자산 100% 존재 또는 경고 승인

### 4. CLAUDE.md 업데이트
프로젝트 CLAUDE.md에 새 섹션 추가:

```markdown
## Claude Code Skills (TASK_030)
로컬 `.claude/skills/` 디렉토리에 매거진 전용 skills 5개 등록됨.
편집자가 자연어로 요청하면 Claude Code가 관련 skill 자동 호출.

- 5개 skill 목록과 사용 예시
- Superpowers 플러그인과 독립적 — 플러그인 설치 없이도 동작
```

### 5. 설치 안내 (README 섹션 또는 별도 파일)
```markdown
# Skills 활성화

## 옵션 1: 로컬만 (권장 — 현재 태스크)
이 프로젝트의 .claude/skills/ 는 Claude Code가 자동 인식합니다.
추가 설치 불필요.

## 옵션 2: Superpowers 플러그인 (선택)
obra/superpowers 공식 플러그인도 함께 사용하려면:
/plugin install superpowers@claude-plugins-official
```

---

## 완료 조건
- [ ] `.claude/skills/` 디렉토리 생성 (5개 skill 폴더)
- [ ] 각 SKILL.md 파일이 frontmatter + 절차 + Verify 섹션 포함
- [ ] 각 skill이 기존 pipeline 모듈과 연결됨 (Bash 명령어로)
- [ ] CLAUDE.md에 Skills 섹션 추가
- [ ] 설치 안내 문서화
- [ ] Claude Code가 자연어 "기사 검토해줘" 등으로 skill 트리거 가능한지 문서에 명시
- [ ] 기존 파이프라인 변경 0줄 (skill은 래퍼 역할만)

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_030 implemented
```

## 주의사항
- Skills는 **프로젝트 내부 `.claude/skills/`** 사용 (사용자 글로벌 skills와 무관)
- SKILL.md 내 Bash 명령은 프로젝트 루트 기준 상대 경로
- 각 skill은 단일 책임 (Single Responsibility) — 복합 작업은 여러 skill 조합
- "Verify before success" 원칙 준수 — 모든 skill은 체크리스트로 검증
