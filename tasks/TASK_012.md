# TASK_012 — 운영환경 체크 스크립트

## 메타
- **status**: todo
- **prerequisites**: 없음
- **예상 소요**: 30분
- **서브에이전트 분할**: 불필요
- **Phase**: 2 (운영 준비)

---

## 목적
주간 브리프 첫 발행 전, 모든 외부 연동이 실제로 작동하는지 5분 안에 확인한다.
`.env` 누락·오타·API 키 무효·DB 권한 문제를 사전에 드러낸다.

---

## 구현 명세

### 생성할 파일: `scripts/check_env.py`

### CLI
```bash
# 전체 체크
python scripts/check_env.py

# 특정 항목만 체크
python scripts/check_env.py --only anthropic ghost

# 실패 시 exit code 1 (CI/n8n 연동용)
python scripts/check_env.py --strict
```

### 체크 항목 (8개)

| # | 이름 | 내용 | 실패 시 안내 |
|---|---|---|---|
| 1 | `.env` 존재 | 파일 존재 여부 | `cp .env.example .env` |
| 2 | `ANTHROPIC_API_KEY` | `client.messages.create()` 에코 테스트 (claude-haiku-4-5-20251001, max_tokens=10) | console.anthropic.com 에서 키 확인 |
| 3 | `GHOST_ADMIN_API_KEY` | JWT 생성 + `/admin/site/` GET 200 응답 | kid:secret 형식 확인 |
| 4 | `GHOST_ADMIN_API_URL` | URL 접근 가능 + HTTPS | URL 확인 |
| 5 | `SOURCE_DB_PATH` | 디렉토리 쓰기 권한 + SQLite 연결 | `data/` 폴더 권한 확인 |
| 6 | `LANGFUSE_*` (선택) | 3개 키 모두 있으면 연결 테스트, 없으면 스킵 | (선택 항목이라 경고만) |
| 7 | Python 패키지 | `anthropic`, `requests`, `python-dotenv`, `PyJWT`, `langfuse` import 가능 | `pip install -r requirements.txt` |
| 8 | 폴더 구조 | `data/`, `drafts/`, `logs/`, `output/` 존재 | 자동 생성 옵션 제공 |

### 출력 형식
```
=== Claude Magazine 운영환경 체크 ===

[1/8] .env 파일
  ✅ /c/Users/shin.buheon/claude-magazine/.env

[2/8] ANTHROPIC_API_KEY
  ✅ 응답 수신 (model=claude-haiku-4-5-20251001, 12 tokens)

[3/8] GHOST_ADMIN_API_KEY
  ❌ JWT 서명 실패 — kid:secret 형식이 아님
     해결: Ghost Admin > Integrations 에서 Admin API Key 복사

[4/8] GHOST_ADMIN_API_URL
  ⏭  스킵 (3번 실패로 종속)

[5/8] SOURCE_DB_PATH
  ✅ ./data/source_registry.db (읽기/쓰기 OK)

[6/8] LANGFUSE_*
  ⚠️  LANGFUSE_PUBLIC_KEY 미설정 — 관측 기능 비활성화

[7/8] Python 패키지
  ✅ 5/5 import 성공

[8/8] 폴더 구조
  ✅ data/ drafts/ logs/ output/ 모두 존재

=== 결과: 6 통과 / 1 실패 / 1 경고 ===
```

### 에러 처리 원칙
- 네트워크 호출은 모두 `timeout=10` 적용
- API 호출 실패 시 HTTP 상태코드·응답 본문 요약 함께 출력
- 한 항목 실패해도 나머지 계속 진행 (`--strict` 모드에서만 중단)

---

## 완료 조건
- [ ] `scripts/check_env.py` 생성
- [ ] 8개 체크 항목 모두 구현
- [ ] `--only`, `--strict` 옵션 동작
- [ ] `.env` 없는 상태에서 실행해도 예외 없이 (1) 항목만 실패로 출력
- [ ] ANTHROPIC_API_KEY 없이 실행해도 (2) 항목만 실패로 출력 (다른 체크 정상 진행)
- [ ] 출력은 시각적으로 읽기 쉬운 표 형식 (이모지 ✅❌⏭⚠️)
- [ ] exit code: 전체 통과 → 0, 하나라도 실패 + `--strict` → 1

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_012 implemented
```
