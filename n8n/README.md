# n8n 워크플로우 — Claude Magazine

Claude Magazine 자동화 파이프라인의 n8n 워크플로우 정의. 3개 워크플로우는 서로 느슨하게 연결된 이벤트 체인으로 동작한다.

```
[Cron 매주 월 09:00 KST]
        │
        ▼
 workflow_1_scheduler.json   ── Slack 알림 ─▶ 편집자 Ghost에서 초안 검수
        │
        ▼ (편집자 승인 시 수동/버튼 POST)
 workflow_2_publish.json     ── run_weekly_brief.py --publish
        │
        ▼ (Ghost 포스트 라이브 → Webhook)
 workflow_3_sns.json          ── channel_rewriter.py × 2 (sns, linkedin)
```

---

## 1. 사전 준비

### 1.1 환경 변수

n8n 인스턴스의 **Settings → Environment Variables** (셀프호스트) 또는 **Credentials / Variables** (n8n Cloud)에 아래 값을 등록한다.

| 이름 | 설명 | 예시 |
|---|---|---|
| `CLAUDE_MAGAZINE_ROOT` | 프로젝트 루트 절대경로 (Execute Command `cwd`) | `/srv/claude-magazine` 또는 `C:\\Users\\shin.buheon\\claude-magazine` |
| `NOTIFY_SLACK_WEBHOOK` | Slack Incoming Webhook URL | `https://hooks.slack.com/services/...` |
| `SOURCE_LIST_URL` | 주간 소스 URL 목록을 반환하는 엔드포인트 (JSON 배열 `[{topic,...}]`) | `https://your-site.ghost.io/api/admin/sources/weekly` |

`.env.example`에 이미 `N8N_WEBHOOK_URL`, `NOTIFY_SLACK_WEBHOOK`이 정의되어 있으므로 Python 측에서는 추가 수정 불필요.

### 1.2 n8n 셀프호스트에서 Python 실행 가능하게 하기

n8n 기본 Docker 이미지에는 Python이 없다. Execute Command 노드가 `python` 을 호출하려면 아래 중 하나를 선택한다.

- **방법 A (권장): 호스트 바인드 마운트**
  ```yaml
  # docker-compose.yml
  services:
    n8n:
      volumes:
        - /srv/claude-magazine:/srv/claude-magazine
      environment:
        - CLAUDE_MAGAZINE_ROOT=/srv/claude-magazine
        - N8N_DEFAULT_BINARY_DATA_MODE=filesystem
  ```
  호스트에서 `cd /srv/claude-magazine && pip install -r requirements.txt` 를 사전에 실행. n8n 컨테이너에 `python3`이 설치되어 있어야 하므로 Dockerfile을 확장해 `apt-get install -y python3 python3-pip` 를 추가한 커스텀 이미지를 사용한다.

- **방법 B: n8n Cloud 사용 시**
  n8n Cloud에서는 Execute Command가 제한된다. 프로젝트 루트에 **SSH 가능한 원격 호스트**를 두고 Execute Command 대신 **SSH 노드**로 교체하거나, Python 파이프라인을 별도 HTTP 서버(예: FastAPI)로 감싸 **HTTP Request 노드**로 호출한다.

---

## 2. 워크플로우 import 방법

### 2.1 n8n Cloud / 셀프호스트 공통

1. 좌측 메뉴 **Workflows → Add workflow → Import from File**
2. `n8n/workflow_1_scheduler.json` 선택 → Import
3. 열린 워크플로우 우측 상단 **...** → **Settings** → Timezone을 `Asia/Seoul` 로 확인
4. 각 Slack 노드의 **Credentials** 를 설정 (아래 2.2 참고) 또는 Webhook URL 모드 그대로 유지
5. **Save** 후 필요 시 **Activate** 토글로 활성화
6. 같은 방식으로 `workflow_2_publish.json`, `workflow_3_sns.json` 도 import

### 2.2 Slack 노드 인증

두 가지 방식 중 택1.

- **(간단) Incoming Webhook 모드**: 워크플로우 JSON은 기본 `authentication: webhook` 로 되어 있어 `NOTIFY_SLACK_WEBHOOK` 환경변수를 그대로 사용한다. 별도 OAuth 불필요.
- **(권장) Slack OAuth2 Credential**: 공식 연동이 필요하면 n8n에서 Slack OAuth2 API credential을 생성하고 각 Slack 노드의 authentication을 `oAuth2` 로 변경, channel 지정.

---

## 3. Webhook URL 정리

import 직후 각 Webhook 노드의 **Test URL / Production URL** 을 복사해 아래 테이블을 채운다.

| 워크플로우 | Webhook 경로 | 용도 |
|---|---|---|
| workflow_2_publish | `POST /webhook/publish-approved` | 편집자 승인 후 발행 트리거 |
| workflow_3_sns | `POST /webhook/ghost-post-published` | Ghost `post.published` 이벤트 수신 |

예시 Production URL (셀프호스트):
```
https://n8n.your-domain.com/webhook/publish-approved
https://n8n.your-domain.com/webhook/ghost-post-published
```

### 3.1 workflow_2 수동 호출 예

```bash
curl -X POST https://n8n.your-domain.com/webhook/publish-approved \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Claude Agent SDK 2026 업데이트",
    "brief_path": "drafts/2026-04-21_brief.md",
    "draft_path": "drafts/2026-04-21_draft.md"
  }'
```

---

## 4. Ghost Webhook 연동 (workflow_3)

Ghost Admin UI에서 `post.published` 이벤트가 발생할 때마다 workflow_3을 호출하도록 설정한다.

1. Ghost Admin → **Settings → Advanced → Integrations**
2. **Add custom integration** 클릭, 이름을 `Claude Magazine SNS Rewriter` 로 지정
3. 생성된 Integration 상세 페이지 하단 **Webhooks → Add webhook**
4. 아래 값을 입력 후 저장
   - **Name**: `post.published → n8n`
   - **Event**: `Post published`
   - **Target URL**: `https://n8n.your-domain.com/webhook/ghost-post-published`
5. Ghost Webhook 페이로드 구조가 `{ post: { current: { ... } } }` 형태이므로, workflow_3 내부 expression은 `$json["body"]["post"]["current"]` 를 사용한다.
6. `draft_path` 가 Ghost 포스트 메타데이터에 포함되지 않는 경우 Ghost 커스텀 필드(예: `codeinjection_head` 또는 내부 태그)에 저장하거나, `pipeline/ghost_client.py` 에서 포스트 슬러그를 기반으로 drafts 경로를 재구성하는 helper 를 사용한다.

### 4.1 Ghost Webhook 검증 (옵션)

Ghost는 webhook secret 을 지원하지 않는다. 보안이 필요하면 n8n Webhook 노드 앞단에 IP allowlist 를 적용하거나 path에 랜덤 토큰(`/webhook/ghost-post-published-<random>`)을 포함한다.

---

## 5. 재시도 / 실패 알림 정책

| 워크플로우 | 재시도 | 실패 알림 |
|---|---|---|
| workflow_1 (Execute Command) | **3회**, 간격 **15분** (`retryOnFail`, `maxTries`, `waitBetweenTries`) | Error Trigger → Slack |
| workflow_2 | 기본 1회 (발행은 멱등성 보장 어려움) | Error Trigger → Slack |
| workflow_3 | 기본 1회 | Error Trigger → Slack |

Slack 알림은 모두 `$env.NOTIFY_SLACK_WEBHOOK` 로 전송되며, 포맷은 워크플로우 JSON의 Slack 노드 `text` 필드에서 확인 가능.

---

## 6. 트러블슈팅

| 증상 | 원인 / 조치 |
|---|---|
| Execute Command 노드에서 `python: command not found` | n8n 컨테이너에 `python3` 미설치. 커스텀 이미지로 교체 또는 SSH 노드로 전환 |
| `cwd not found` | `CLAUDE_MAGAZINE_ROOT` 환경변수 누락. n8n Variables 에 추가 |
| Slack 메시지에 `{{...}}` 템플릿이 그대로 노출 | 해당 필드가 expression 모드가 아님. 입력창에 `=` 접두어 확인 |
| workflow_3가 draft_path 를 찾지 못함 | Ghost 페이로드에 draft_path 가 없음. `pipeline/ghost_client.py` 에서 slug→path resolver 추가 필요 |
| Cron이 한국시간과 다르게 동작 | 워크플로우 Settings → Timezone 을 `Asia/Seoul` 로 명시 |

---

## 7. 파일 목록

```
n8n/
├── workflow_1_scheduler.json   # Cron 매주 월 09:00 KST → 브리프 dry-run → Slack
├── workflow_2_publish.json     # Webhook /publish-approved → publish → Slack
├── workflow_3_sns.json         # Ghost post.published → SNS/LinkedIn 재가공 → Slack
└── README.md                   # 이 문서
```
