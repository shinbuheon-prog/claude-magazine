# TASK_020 — 국내 결제 연동 (PortOne billingkey + 스케줄 결제)

## 메타
- **status**: todo
- **prerequisites**: TASK_002
- **예상 소요**: 90분
- **서브에이전트 분할**: 가능 (A: billingkey 발급 / B: 스케줄 결제 / C: 웹훅 수신)
- **Phase**: 3 (수익화 블로커 해소)

---

## 목적
Ghost 네이티브 결제는 Stripe 전용 → **국내 정기결제(자동결제) 블로커**.
리포트 인용: _"한국형 기본안: PortOne 빌링키 발급 + 월간 반복 결제. Toss Payments는 API 직접 구축 필요."_

---

## 구현 명세

### 생성할 파일 (3개)
```
pipeline/
├── portone_client.py           ← A: 빌링키 발급 + 결제 트리거
└── subscription_scheduler.py   ← B: 월간 스케줄 결제

scripts/
└── portone_webhook_server.py   ← C: PortOne 웹훅 수신 서버 (FastAPI)
```

### A: portone_client.py

```python
def issue_billing_key(customer_id: str, card_info: dict) -> dict:
    """
    POST /billing-keys
    반환: {"billing_key": str, "customer_id": str, "expires_at": str}
    """

def charge(billing_key: str, amount: int, order_name: str, order_id: str) -> dict:
    """
    POST /payments/{order_id}/schedules 또는 /payments/{order_id}/billing-key-payment
    반환: {"payment_id": str, "status": "PAID|FAILED", "receipt_url": str}
    """

def get_payment(payment_id: str) -> dict:
    """GET /payments/{id}"""

def cancel_payment(payment_id: str, reason: str) -> dict:
    """POST /payments/{id}/cancel"""
```

### B: subscription_scheduler.py

```python
def create_subscription(
    customer_id: str,
    billing_key: str,
    tier: str,  # "monthly" | "annual"
    amount: int,
) -> dict:
    """
    SQLite subscriptions 테이블에 등록.
    반환: {"subscription_id": str, "next_charge_at": str}
    """

def run_monthly_charges(dry_run: bool = False) -> list[dict]:
    """
    매일 00:00 KST Cron → 오늘 결제일인 구독 모두 조회 → charge()
    실패 시: 3일 재시도 → 그래도 실패면 구독 정지 + Slack 알림
    반환: [{"subscription_id", "status", "payment_id"}, ...]
    """
```

### SQLite 스키마 (subscriptions.db)
```sql
CREATE TABLE subscriptions (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    billing_key TEXT NOT NULL,
    tier TEXT NOT NULL,          -- monthly | annual
    amount INTEGER NOT NULL,
    status TEXT NOT NULL,        -- active | paused | canceled
    started_at TEXT NOT NULL,
    next_charge_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE payments (
    id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL,
    portone_payment_id TEXT,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL,        -- paid | failed | canceled
    attempted_at TEXT NOT NULL,
    succeeded_at TEXT,
    failure_reason TEXT,
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
);
```

### C: portone_webhook_server.py (FastAPI)

```python
@app.post("/webhook/portone")
async def portone_webhook(request: Request):
    """
    PortOne 결제 완료/실패/취소 이벤트 수신.
    1. 서명 검증 (X-Portone-Signature 헤더)
    2. payments 테이블 상태 업데이트
    3. 결제 성공 → Ghost members API로 티어 업그레이드
    4. 결제 실패 3회 → 구독 정지 + Slack 알림
    """
```

### CLI
```bash
# 월간 결제 실행 (n8n Cron에서 호출)
python pipeline/subscription_scheduler.py --run-charges

# 드라이런
python pipeline/subscription_scheduler.py --run-charges --dry-run

# 웹훅 서버 실행
python scripts/portone_webhook_server.py --port 8000

# 빌링키 발급 테스트
python pipeline/portone_client.py issue-key --customer-id cust-001 --card-file card.json
```

### .env 추가
```
PORTONE_STORE_ID=store-...
PORTONE_API_SECRET=...
PORTONE_WEBHOOK_SECRET=...
SUBSCRIPTION_DB_PATH=./data/subscriptions.db
```

### n8n workflow_4_monthly_charge.json 추가
매일 00:00 KST Cron → `python pipeline/subscription_scheduler.py --run-charges` → Slack 알림

---

## 완료 조건
- [ ] `pipeline/portone_client.py` 생성 (billingkey + 결제 API)
- [ ] `pipeline/subscription_scheduler.py` 생성 (SQLite + 스케줄 로직)
- [ ] `scripts/portone_webhook_server.py` 생성 (FastAPI + 서명 검증)
- [ ] `data/subscriptions.db` 스키마 마이그레이션 스크립트
- [ ] `.env.example`에 4개 항목 추가
- [ ] `--dry-run` 모드 전부 지원
- [ ] Ghost members API 연동 확인 (결제 성공 시 티어 업그레이드)
- [ ] 결제 실패 3회 재시도 후 구독 정지 로직 검증
- [ ] 스모크 테스트: PortOne 테스트 키로 end-to-end

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_020 implemented
```

---

## 주의사항
- PortOne v2 API 사용 (`https://api.portone.io`) — v1은 deprecated
- 웹훅 서명 검증 누락 시 **위조 결제 완료 알림** 리스크 — HMAC-SHA256 필수
- 테스트 모드와 라이브 모드 환경변수 분리 (PORTONE_MODE=test|live)
- 결제 실패 사유별 분기 (잔액부족·카드만료·본인인증필요) — 사용자 안내 차별화
