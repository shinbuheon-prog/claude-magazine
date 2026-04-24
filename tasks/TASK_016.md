# TASK_016 — 편집 체크리스트 자동 검증 (editorial_lint.py)

## 메타
- **status**: todo
- **prerequisites**: TASK_003, TASK_005
- **예상 소요**: 45분
- **서브에이전트 분할**: 불필요
- **Phase**: 3 (품질 게이트)

---

## 목적
`docs/editorial_checklist.md`의 10개 항목을 Ghost 발행 **전 필수 게이트**로 자동 검증한다.
리포트 인용: _"게시 전 필수 통과 폼으로 구현. CMS 게시 전 모든 항목 통과해야 발행 버튼 활성화."_

---

## 구현 명세

### 생성할 파일: `pipeline/editorial_lint.py`

### CLI
```bash
# 초안 파일 검증
python pipeline/editorial_lint.py --draft drafts/article.md

# 특정 항목만
python pipeline/editorial_lint.py --draft drafts/article.md --only source-id disclosure

# JSON 리포트 출력
python pipeline/editorial_lint.py --draft drafts/article.md --json

# Ghost 포스트 ID로 검증 (이미 draft로 올라간 경우)
python pipeline/editorial_lint.py --ghost-post-id POST_ID

# CI 모드 (실패 시 exit 1)
python pipeline/editorial_lint.py --draft drafts/article.md --strict
```

### 검증 10개 항목 (editorial_checklist.md 매핑)

| # | 이름 | 검증 방법 | 실패 시 메시지 |
|---|---|---|---|
| 1 | `source-id` | 모든 주장 문장 끝에 `[src-xxx]` 또는 `(source_id: ...)` 존재 | "N개 문장에 source_id 없음" |
| 2 | `translation-guard` | 번역 인용이 3줄 이상 연속이면 경고 (저작권) | "장문 인용 N건" |
| 3 | `title-body-match` | Sonnet에게 제목-본문 일치도 판정 호출 (0~100) | "일치도 XX점" |
| 4 | `quote-fidelity` | source_registry에서 원문 fetch 후 인용 일치 확인 | "인용 N건 원문 불일치" |
| 5 | `no-fabrication` | 수치·기업명·사례명이 source 내에 존재하는지 grep | "근거 없는 수치 N건" |
| 6 | `pii-check` | 이름·전화·이메일·주민번호 패턴 탐지 | "PII 의심 N건" |
| 7 | `image-rights` | 이미지 태그에 `data-rights` 속성 필수 | "라이선스 미기록 이미지 N건" |
| 8 | `ai-disclosure` | 문서 하단에 AI 사용 고지 문구 존재 | "AI 사용 고지 누락" |
| 9 | `correction-policy` | 정정 책임자·24h 응답 기한 명시 | "정정 정책 누락" |
| 10 | `request-id-log` | `logs/`에 해당 draft의 request_id 기록 존재 | "API 로그 누락" |

### 출력 형식
```
=== 편집 체크리스트 검증 ===
파일: drafts/article_20260421.md

[ 1/10] source-id                  ✅ 모든 주장에 source_id 연결 (42개)
[ 2/10] translation-guard          ⚠️  장문 인용 1건 (48줄) — 3번째 단락
[ 3/10] title-body-match           ✅ 일치도 87점
[ 4/10] quote-fidelity             ❌ 인용 2건 원문 불일치
                                      - "약 30%" → 원문 "28.7%"
                                      - "최초로"  → 원문 "두번째로"
[ 5/10] no-fabrication             ✅ 근거 있는 수치만 사용
[ 6/10] pii-check                  ✅ PII 패턴 미탐지
[ 7/10] image-rights               ❌ 라이선스 미기록 2건
[ 8/10] ai-disclosure              ❌ AI 사용 고지 문구 누락
[ 9/10] correction-policy          ✅ 정정 정책 명시
[10/10] request-id-log             ✅ logs/brief_20260421.json 확인

=== 결과: 6 통과 / 3 실패 / 1 경고 ===
발행 불가 — 실패 항목을 수정하세요.
```

### 함수 시그니처
```python
def lint_draft(draft_path: str, only: list[str] | None = None) -> dict:
    """
    반환: {
        "passed": int,
        "failed": int,
        "warnings": int,
        "items": [
            {"id": "source-id", "status": "pass|fail|warn", "message": "..."},
            ...
        ],
        "can_publish": bool
    }
    """
```

### Ghost 통합 (선택)
- `--ghost-post-id` 지정 시 Ghost Content API로 HTML fetch → 검증
- 실패 시 `POST /admin/posts/:id/` 로 `status=draft` 유지 (발행 차단)

---

## 완료 조건
- [ ] `pipeline/editorial_lint.py` 생성
- [ ] 10개 체크 항목 전부 구현
- [ ] `--only`, `--json`, `--strict`, `--ghost-post-id` 옵션 동작
- [ ] 항목 중 하나라도 실패 + `--strict` → exit 1
- [ ] 발행 게이트 동작: 실패 시 `can_publish: False` 반환
- [ ] 스모크 테스트: 가짜 draft로 10개 항목 전부 실행 확인

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_016 implemented
```
