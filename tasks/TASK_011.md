# TASK_011 — develop → main 머지 + v0.1.0 릴리즈

## 메타
- **status**: todo
- **prerequisites**: TASK_012, TASK_013 (운영 검증 완료 후)
- **예상 소요**: 15분
- **서브에이전트 분할**: 불필요
- **Phase**: 2 (안정화 릴리즈)

---

## 목적
Phase 1 전체 구현(TASK_001~010) + Phase 2 운영 준비(TASK_012, 013)가 완료된 상태를
`main` 브랜치로 승격하고 `v0.1.0` 시맨틱 버전 태그를 찍는다.

---

## 구현 명세

### 1. 사전 체크
```bash
# develop 브랜치가 최신 상태인지 확인
git checkout develop && git pull origin develop

# 운영환경 체크 전체 통과
python scripts/check_env.py --strict

# E2E 스모크 테스트 통과
python scripts/test_e2e.py
```

### 2. main 머지 (fast-forward 금지, merge commit 유지)
```bash
git checkout main && git pull origin main
git merge --no-ff develop -m "Release v0.1.0 — Phase 1·2 완료"
git push origin main
```

### 3. 태그 생성 및 릴리즈
```bash
git tag -a v0.1.0 -m "$(cat <<'EOF'
v0.1.0 — Claude Magazine 초기 릴리즈

## 포함된 기능
### Phase 1 (TASK_001~010)
- Claude API 3단 파이프라인 (Sonnet·Opus·Haiku)
- Ghost CMS 연동 (Admin API, 뉴스레터 발송)
- 출처 레지스트리 (SQLite)
- 팩트체크 에이전트 (Opus 4.7)
- n8n 워크플로우 3종 (스케줄러·발행·SNS 재가공)
- Langfuse 관측 연동
- React 매거진 레이아웃 + Recharts
- Puppeteer 월간 PDF 생성

### Phase 2 (TASK_012, 013)
- 운영환경 체크 스크립트 (8개 항목)
- E2E 스모크 테스트 (전체 흐름 mock 검증)
EOF
)"

git push origin v0.1.0
```

### 4. GitHub Release 생성
```bash
gh release create v0.1.0 \
  --title "v0.1.0 — Claude Magazine 초기 릴리즈" \
  --notes-file CHANGELOG.md \
  --target main
```

### 5. CHANGELOG.md 생성
프로젝트 루트에 `CHANGELOG.md` 생성 — v0.1.0 섹션에 Phase 1·2 태스크 목록 기록.

---

## 완료 조건
- [ ] `develop` → `main` fast-forward 아닌 merge commit으로 머지
- [ ] `v0.1.0` 태그 생성 및 push
- [ ] GitHub Release 페이지에 v0.1.0 노출
- [ ] `CHANGELOG.md` 루트에 생성
- [ ] main 브랜치에서 `python scripts/check_env.py` 실행 시 구조 정상

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_011 implemented
```

---

## 주의사항
- `--no-ff` 플래그 필수 (커밋 이력 보존)
- 태그는 반드시 annotated tag (`-a`) — 릴리즈 노트 포함
- `main` 브랜치에는 직접 커밋 금지, 반드시 머지로만 변경
