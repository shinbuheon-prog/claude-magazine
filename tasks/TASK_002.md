# TASK_002 — Ghost CMS 연동

## 메타
- **status**: todo
- **prerequisites**: TASK_001
- **예상 소요**: 30분
- **서브에이전트 분할**: 불필요

---

## 목적
Ghost Admin API와 파이프라인을 연결한다.
전면 무료 공개 구조 (페이월 없음), 뉴스레터 구독으로 인바운드 수집.

---

## 구현 명세

### 생성할 파일: `pipeline/ghost_client.py`

```python
"""Ghost Admin API 클라이언트"""
import jwt, requests, time, os
from dotenv import load_dotenv
load_dotenv()

def _get_token() -> str:
    key = os.environ["GHOST_ADMIN_API_KEY"]
    api_url = os.environ["GHOST_ADMIN_API_URL"]
    kid, secret = key.split(":")
    iat = int(time.time())
    token = jwt.encode(
        {"iat": iat, "exp": iat + 300, "aud": "/admin/"},
        bytes.fromhex(secret),
        algorithm="HS256",
        headers={"alg": "HS256", "kid": kid, "typ": "JWT"},
    )
    return token, api_url

def create_post(title: str, html: str, status: str = "draft") -> dict:
    """
    포스트 생성.
    status: "draft" | "published"
    반환: {"post_id": str, "url": str, "status": str}
    """
    # 구현

def send_newsletter(post_id: str) -> dict:
    """
    발행된 포스트를 뉴스레터로 발송.
    반환: {"newsletter_id": str, "recipient_count": int}
    """
    # 구현

if __name__ == "__main__":
    # 스모크 테스트: draft 포스트 생성 후 출력
    result = create_post("테스트 포스트", "<p>테스트 본문</p>", status="draft")
    print(result)
```

### .env에 추가할 항목 (`.env.example`에 이미 있음)
```
GHOST_ADMIN_API_URL=https://your-site.ghost.io
GHOST_ADMIN_API_KEY=kid:secret
```

---

## 완료 조건
- [ ] `pipeline/ghost_client.py` 생성
- [ ] `create_post()` 호출 시 Ghost에 draft 포스트 생성 확인
- [ ] `send_newsletter()` 함수 구조 완성 (Ghost Newsletter API 연동)
- [ ] 스모크 테스트 통과: `python pipeline/ghost_client.py`

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_002 implemented
```
