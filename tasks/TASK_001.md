# TASK_001 — 프로젝트 초기 설정

## 메타
- **status**: todo
- **prerequisites**: 없음
- **예상 소요**: 10분
- **서브에이전트 분할**: 불필요 (단순 파일/폴더 생성)

---

## 목적
파이프라인 실행에 필요한 디렉토리와 환경 설정을 완성하고
Codex 보드를 초기화한다.

---

## 구현 명세

### 생성할 폴더
```
claude-magazine/data/      # SQLite DB 저장
claude-magazine/drafts/    # 생성된 초안 저장
claude-magazine/logs/      # API request_id 로그 저장
```

### 생성할 파일: `.gitignore` (없으면 생성, 있으면 항목 추가)
```
.env
data/
drafts/
logs/
__pycache__/
*.pyc
.DS_Store
```

### 실행할 커맨드
```bash
# 보드 초기화
python codex_workflow.py sync

# 확인
python codex_workflow.py list
```

---

## 완료 조건 (체크리스트)
- [ ] `data/`, `drafts/`, `logs/` 폴더 존재 확인
- [ ] `.env.example` → `.env` 복사 안내 메시지 출력
- [ ] `python codex_workflow.py sync` 실행 시 8개 태스크 출력
- [ ] `python codex_workflow.py list` 실행 시 오류 없음

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_001 implemented
```
