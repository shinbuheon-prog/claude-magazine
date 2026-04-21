# TASK_014 — n8n 워크플로우 import 자동화

## 메타
- **status**: todo
- **prerequisites**: TASK_007
- **예상 소요**: 30분
- **서브에이전트 분할**: 불필요
- **Phase**: 2 (운영 준비)

---

## 목적
`n8n/` 폴더의 3개 JSON 워크플로우를 한 커맨드로 n8n 인스턴스에 import한다.
수동 UI 클릭 의존성을 제거해 재배포·롤백을 빠르게 한다.

---

## 구현 명세

### 생성할 파일: `scripts/n8n_import.py`

### CLI
```bash
# 전체 워크플로우 import
python scripts/n8n_import.py

# 특정 워크플로우만
python scripts/n8n_import.py --workflow workflow_1_scheduler.json

# 기존 워크플로우 덮어쓰기
python scripts/n8n_import.py --overwrite

# 드라이런 (실제 import 없이 API 호출 미리보기)
python scripts/n8n_import.py --dry-run
```

### .env 추가 항목
```
N8N_BASE_URL=https://your-n8n-instance.n8n.cloud
N8N_API_KEY=n8n_api_...
```
→ `.env.example` 에도 추가

### 동작 흐름
```
1. .env 에서 N8N_BASE_URL, N8N_API_KEY 읽기
2. GET /rest/workflows → 기존 워크플로우 이름 조회
3. n8n/workflow_*.json 파일 순회
4. 각 파일에 대해:
   a. 같은 이름 워크플로우 존재 여부 확인
   b. 존재 + --overwrite → PUT /rest/workflows/{id}
   c. 존재 + --overwrite 없음 → 스킵 (경고 출력)
   d. 없음 → POST /rest/workflows
5. import 성공한 워크플로우 목록 출력
```

### n8n REST API 엔드포인트 (n8n Cloud / 셀프호스트 공통)
```
GET    /rest/workflows              # 전체 목록
POST   /rest/workflows              # 신규 생성
PUT    /rest/workflows/:id          # 업데이트
GET    /rest/workflows/:id          # 단건 조회
POST   /rest/workflows/:id/activate # 활성화
```

인증: `X-N8N-API-KEY: {N8N_API_KEY}` 헤더

### 출력 형식
```
=== n8n 워크플로우 Import ===

[1/3] workflow_1_scheduler.json
  ℹ️  기존 워크플로우 발견 (id: 42, 이름: "Claude Magazine — Scheduler")
  ✅ PUT 성공 — 업데이트됨

[2/3] workflow_2_publish.json
  ✅ POST 성공 — 신규 생성 (id: 43)

[3/3] workflow_3_sns.json
  ⏭  스킵 — 이미 존재함 (--overwrite 없음)

=== 결과: 2 성공 / 0 실패 / 1 스킵 ===

활성화하려면:
  n8n UI 에서 각 워크플로우의 "Active" 토글 ON
```

### 에러 처리
- API 키 누락 → 즉시 에러 종료 (exit 1)
- 네트워크 timeout → 각 파일당 최대 3회 재시도 (15초 간격)
- JSON 파싱 실패 → 파일명 + 에러 출력 후 다음 파일로 진행
- 401/403 응답 → API 키 확인 안내

---

## 완료 조건
- [ ] `scripts/n8n_import.py` 생성
- [ ] `--workflow`, `--overwrite`, `--dry-run` 옵션 동작
- [ ] `.env.example` 에 N8N_BASE_URL, N8N_API_KEY 추가
- [ ] 드라이런 실행 시 실제 API 호출 없이 요청 본문 미리보기 출력
- [ ] 네트워크 실패 시 3회 재시도 확인
- [ ] 출력에 import된 워크플로우 ID 포함

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_014 implemented
```
