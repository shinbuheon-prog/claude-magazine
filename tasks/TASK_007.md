# TASK_007 — n8n 워크플로우 자동화

## 메타
- **status**: todo
- **prerequisites**: TASK_003, TASK_004, TASK_005, TASK_006
- **예상 소요**: 60분
- **서브에이전트 분할**: 가능 (워크플로우 3개 독립 설계)

---

## 목적
n8n으로 3개 워크플로우를 구성해 수동 트리거를 최소화한다.

---

## 서브에이전트 A: 워크플로우 1 — 소스 수집 스케줄러

### n8n JSON 정의 (파일: `n8n/workflow_1_scheduler.json`)
```
Cron node (매주 월 09:00 KST)
  → HTTP Request node (소스 URL 목록 fetch)
  → Execute Command node
      cmd: "python scripts/run_weekly_brief.py --topic {{$json.topic}} --dry-run"
  → Slack node (편집자 알림: "브리프 생성 완료, Ghost 확인 후 발행하세요")
```

### 실패 처리
```
Error trigger → Slack node ("워크플로우 1 실패: {{$json.error}}")
재시도: 15분 간격 3회
```

---

## 서브에이전트 B: 워크플로우 2 — 편집자 승인 후 발행

### n8n JSON 정의 (파일: `n8n/workflow_2_publish.json`)
```
Webhook node (POST /webhook/publish-approved)
  body: {topic, brief_path, draft_path}
  → Execute Command node
      cmd: "python scripts/run_weekly_brief.py --topic {{$json.topic}} --publish"
  → Slack node ("발행 완료: {{$json.url}}")
```

---

## 서브에이전트 C: 워크플로우 3 — SNS 재가공

### n8n JSON 정의 (파일: `n8n/workflow_3_sns.json`)
```
Webhook node (Ghost post.published 이벤트 수신)
  → Execute Command node
      cmd: "python pipeline/channel_rewriter.py --draft {{$json.draft_path}} --channel sns"
  → Execute Command node
      cmd: "python pipeline/channel_rewriter.py --draft {{$json.draft_path}} --channel linkedin"
  → Slack node ("SNS 초안 생성 완료, 검토 후 게시하세요")
```

---

## 생성할 파일
```
claude-magazine/
└── n8n/
    ├── workflow_1_scheduler.json
    ├── workflow_2_publish.json
    └── workflow_3_sns.json
```

---

## .env에 추가할 항목
```
N8N_WEBHOOK_URL=https://your-n8n/webhook/...
NOTIFY_SLACK_WEBHOOK=https://hooks.slack.com/...
```

---

## 완료 조건
- [ ] `n8n/` 폴더 및 3개 JSON 파일 생성
- [ ] n8n Cloud에 각 워크플로우 import 가능한 형태
- [ ] 워크플로우 1: Cron 트리거 설정 확인
- [ ] 워크플로우 2: Webhook 수신 URL 문서화
- [ ] 워크플로우 3: Ghost Webhook 연동 설정 방법 README에 기록

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_007 implemented
```
