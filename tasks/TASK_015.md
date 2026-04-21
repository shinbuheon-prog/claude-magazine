# TASK_015 — Ghost Webhook 자동 등록

## 메타
- **status**: todo
- **prerequisites**: TASK_002
- **예상 소요**: 30분
- **서브에이전트 분할**: 불필요
- **Phase**: 2 (운영 준비)

---

## 목적
Ghost CMS의 `post.published` 이벤트를 n8n workflow_3_sns Webhook으로 자동 등록한다.
SNS 재가공 자동화의 마지막 연결 고리.

---

## 구현 명세

### 생성할 파일: `pipeline/ghost_webhook_setup.py`

### CLI
```bash
# Webhook 등록
python pipeline/ghost_webhook_setup.py --register

# 기존 Webhook 목록 조회
python pipeline/ghost_webhook_setup.py --list

# 특정 Webhook 삭제
python pipeline/ghost_webhook_setup.py --delete WEBHOOK_ID

# 드라이런 (실제 등록 없이 요청 미리보기)
python pipeline/ghost_webhook_setup.py --register --dry-run
```

### 함수 시그니처
```python
def register_webhook(
    event: str = "post.published",
    target_url: str | None = None,
    name: str = "Claude Magazine — SNS Rewriter",
) -> dict:
    """
    Ghost Admin API POST /admin/webhooks/
    target_url 기본값: N8N_WEBHOOK_URL 환경변수 + /webhook/ghost-post-published
    반환: {webhook_id, event, target_url, status}
    """

def list_webhooks() -> list[dict]:
    """GET /admin/webhooks/ → 등록된 webhook 목록"""

def delete_webhook(webhook_id: str) -> bool:
    """DELETE /admin/webhooks/:id"""
```

### Ghost Webhook 지원 이벤트 (참고)
- `post.published` — 포스트 발행 시
- `post.added` — 포스트 생성 시
- `post.edited` — 포스트 수정 시
- `post.unpublished` — 발행 취소 시
- `page.published` / `page.edited`
- `site.changed`

본 태스크는 `post.published` 만 등록 (SNS 재가공 트리거용).

### 인증
`pipeline/ghost_client.py` 의 `_get_token()` 재사용 (JWT 생성 로직 중복 금지).

### 출력 형식
```
=== Ghost Webhook 등록 ===

기존 등록 확인:
  ℹ️  1개 등록되어 있음
     - id: 62a1b..., event: post.published, url: https://old-n8n...

새 Webhook 등록:
  ✅ id: 62a1c..., event: post.published
     target: https://your-n8n/webhook/ghost-post-published

=== 완료 ===
n8n workflow_3_sns 가 활성 상태인지 확인하세요.
```

### 보안 처리
- target_url 은 HTTPS 강제
- n8n webhook에 검증 토큰 추가 권장 (쿼리스트링 또는 헤더)
- 같은 event + target_url 조합은 중복 등록 방지

---

## 완료 조건
- [ ] `pipeline/ghost_webhook_setup.py` 생성
- [ ] `--register`, `--list`, `--delete`, `--dry-run` 옵션 동작
- [ ] JWT 인증은 `ghost_client._get_token()` 재사용 (중복 구현 금지)
- [ ] 중복 Webhook 자동 감지 (같은 event + target_url 조합)
- [ ] target_url HTTPS 검증
- [ ] `--list` 로 등록된 webhook ID 확인 가능

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_015 implemented
```
