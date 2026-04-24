# TASK_024 — Ghost Self-Hosted 배포 자동화

## 메타
- **status**: todo
- **prerequisites**: 없음 (TASK_002와 독립 — Ghost API 연동 코드는 재사용)
- **예상 소요**: 90분
- **서브에이전트 분할**: 가능 (A: Docker 구성 / B: 배포 가이드 / C: SMTP 연동)
- **Phase**: 3 확장 (인프라 독립)

---

## 목적
Ghost(Pro) 14일 무료 트라이얼 만료 회피. **Ghost 오픈소스를 셀프호스팅**하여 기존 `ghost_client.py` 코드 100% 재활용하면서 월 고정비 $0으로 영구 운영.

---

## 배경 및 선택 근거

| 항목 | Ghost(Pro) | Ghost Self-Hosted |
|---|---|---|
| 월 비용 | $18~ (14일 이후) | **$0** (무료 클라우드 + 무료 SMTP) |
| Admin API | 동일 | 동일 |
| JWT 인증 | 동일 | 동일 |
| ghost_client.py 재사용 | ✅ | ✅ (URL만 교체) |
| 유지보수 | Anthropic 책임 | 사용자 책임 (매월 1회 `docker pull` 수준) |
| 구독자·발송 제한 | Starter 500명 | **무제한** (SMTP 쿼터만 주의) |

결론: **Self-Hosted가 비용·코드·기능 모든 면에서 우위**. 유지보수 오버헤드만 월 10분 내외.

---

## 구현 명세

### 1. 생성할 파일 구조
```
deploy/
├── docker-compose.yml          ← Ghost + SQLite (또는 MySQL) 구성
├── README.md                   ← 배포 메인 가이드 (3개 시나리오)
├── oracle-cloud.md             ← Oracle Cloud Always Free 배포 절차
├── fly-io.md                   ← Fly.io Free 배포 절차 (대안)
├── smtp-setup.md               ← Resend / Mailgun SMTP 연동
├── cloudflare-tunnel.md        ← Cloudflare Tunnel로 무료 HTTPS
├── .env.deploy.example         ← 배포용 환경변수 템플릿
└── scripts/
    ├── ghost_backup.sh         ← content/ + DB 일일 백업 스크립트
    └── ghost_update.sh         ← Ghost 버전 업데이트 스크립트
```

### 2. docker-compose.yml (SQLite 기반, 단일 컨테이너)

```yaml
services:
  ghost:
    image: ghost:5-alpine
    container_name: claude-magazine-ghost
    restart: unless-stopped
    ports:
      - "2368:2368"
    environment:
      url: ${GHOST_URL}
      database__client: sqlite3
      database__connection__filename: /var/lib/ghost/content/data/ghost.db
      database__useNullAsDefault: true
      mail__transport: SMTP
      mail__from: ${MAIL_FROM}
      mail__options__service: ${SMTP_SERVICE}       # "Mailgun" | "SendGrid" | "Resend"
      mail__options__host: ${SMTP_HOST}
      mail__options__port: ${SMTP_PORT}
      mail__options__secure: ${SMTP_SECURE}
      mail__options__auth__user: ${SMTP_USER}
      mail__options__auth__pass: ${SMTP_PASS}
      NODE_ENV: production
    volumes:
      - ghost_content:/var/lib/ghost/content
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:2368/ghost/api/admin/site/"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  ghost_content:
    driver: local
```

**SQLite 선택 이유**: MVP 규모(월간 발행·구독자 1,000명 미만)에서 MySQL 오버헤드 불필요.
구독자 10,000명 초과 시 MySQL로 마이그레이션 필요 (가이드에 명시).

### 3. `.env.deploy.example`

```
# Ghost 기본
GHOST_URL=https://magazine.your-domain.dev
MAIL_FROM=noreply@your-domain.dev

# SMTP (Resend 추천 — 월 3,000건 무료)
SMTP_SERVICE=Resend
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=resend
SMTP_PASS=re_xxxxxxxxxxxx

# 대안: Mailgun (100/일 무료)
# SMTP_SERVICE=Mailgun
# SMTP_HOST=smtp.mailgun.org
# SMTP_USER=postmaster@mg.your-domain.dev
# SMTP_PASS=...

# 대안: Amazon SES (처음 $0.10/1000, 저비용)
# SMTP_SERVICE=SES
# SMTP_HOST=email-smtp.ap-northeast-2.amazonaws.com
```

### 4. README.md 구조 (배포 시나리오 3개)

**시나리오 1: Oracle Cloud Always Free (권장)**
- ARM 4코어 / 24GB RAM / 200GB 스토리지 무료 (영구)
- Ubuntu 22.04 ARM64 인스턴스 생성
- Docker 설치 → git clone → `docker compose up -d`
- Cloudflare Tunnel로 무료 HTTPS + 도메인

**시나리오 2: Fly.io Free**
- `fly launch` 한 번이면 자동 배포
- 3 shared-cpu VMs 무료
- 도메인은 `*.fly.dev` 기본 제공 또는 custom

**시나리오 3: 로컬 테스트 (개발용)**
- `docker compose up -d` → `http://localhost:2368`
- Cloudflare Tunnel로 외부 노출 가능

### 5. `deploy/scripts/ghost_backup.sh`

```bash
#!/bin/bash
# 매일 00:00 KST cron 실행 권장
set -e
BACKUP_DIR="${BACKUP_DIR:-/var/backups/ghost}"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

docker compose exec -T ghost tar czf - -C /var/lib/ghost/content . \
  > "$BACKUP_DIR/ghost_content_${DATE}.tar.gz"

# 30일 이상 된 백업 제거
find "$BACKUP_DIR" -name "ghost_content_*.tar.gz" -mtime +30 -delete

echo "Backup complete: ghost_content_${DATE}.tar.gz"
```

### 6. `deploy/scripts/ghost_update.sh`

```bash
#!/bin/bash
# Ghost 마이너 버전 업데이트 — 월 1회 권장
set -e
cd "$(dirname "$0")/.."

echo "Backup before update..."
./scripts/ghost_backup.sh

echo "Pulling latest Ghost 5.x image..."
docker compose pull ghost

echo "Restarting Ghost..."
docker compose up -d ghost

echo "Waiting for health check..."
sleep 30
docker compose ps
```

### 7. Cloudflare Tunnel 가이드 (cloudflare-tunnel.md)

공개 IP 노출 없이 무료 HTTPS + 도메인 연결:
```bash
# Cloudflare 계정 + 도메인 필요 (도메인만 유료, 뉴스레터 운영에 필수)
cloudflared tunnel login
cloudflared tunnel create claude-magazine
cloudflared tunnel route dns claude-magazine magazine.your-domain.dev
cloudflared tunnel run --url http://localhost:2368 claude-magazine
```

### 8. `.env.example` 업데이트

기존 파일 하단에 추가 (기존 줄 보존):
```
# ─── TASK_024: Ghost Self-Hosted 사용 시 ───
# GHOST_ADMIN_API_URL을 셀프호스팅 도메인으로 교체
# 예: GHOST_ADMIN_API_URL=https://magazine.your-domain.dev
```

### 9. 기존 코드와의 연결 검증
**재작성 없음 — URL만 교체**:
- `pipeline/ghost_client.py`: `GHOST_ADMIN_API_URL` 환경변수만 셀프호스팅 URL로
- `pipeline/ghost_webhook_setup.py`: 동일
- `pipeline/disclosure_injector.py`: 동일
- `scripts/check_env.py`: Ghost 체크 로직 그대로 작동 (실제 self-hosted 연결 테스트)

---

## 스모크 테스트 (선택 — 실환경 배포 후)

```bash
# 로컬에서 docker compose로 Ghost 기동
cd deploy && docker compose up -d

# 기동 대기
sleep 60

# 초기 설정 (브라우저에서 http://localhost:2368/ghost/ 접속 → Admin 계정 생성)

# Admin API Key 발급 후 .env에 입력
# GHOST_ADMIN_API_URL=http://localhost:2368
# GHOST_ADMIN_API_KEY=발급받은_kid:secret

# 체크
cd ..
python scripts/check_env.py --only ghost
# → ✅ GHOST_ADMIN_API_KEY 통과

# 기존 파이프라인 동작 확인
python pipeline/ghost_client.py  # 내장 스모크 테스트
```

---

## 완료 조건
- [ ] `deploy/docker-compose.yml` 생성 (Ghost 5.x + SQLite + 헬스체크)
- [ ] `deploy/README.md` 작성 (3개 시나리오)
- [ ] `deploy/oracle-cloud.md`, `fly-io.md`, `smtp-setup.md`, `cloudflare-tunnel.md` 가이드 작성
- [ ] `deploy/.env.deploy.example` 생성
- [ ] `deploy/scripts/ghost_backup.sh`, `ghost_update.sh` 생성
- [ ] `.env.example`에 셀프호스팅 주석 추가 (기존 줄 보존)
- [ ] docker-compose.yml이 **로컬에서 `docker compose up -d` 실행 시 2368 포트에 Ghost 기동** (스모크 테스트로 검증)
- [ ] 기존 `pipeline/ghost_client.py` 코드 변경 0줄 (재활용률 100% 검증)
- [ ] README에 MySQL 마이그레이션 경로 명시 (구독자 10,000명 초과 시)

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_024 implemented
```

---

## 주의사항
- **Ghost 5.x는 Alpine 이미지 존재** (`ghost:5-alpine`) — 용량 절반
- **SQLite는 volume 마운트 필수** — 재시작 시 데이터 유실 방지
- **SMTP 쿼터 주의**: Resend 100/일 = 구독자 500명까지 주 1회 발송 가능
- **Cloudflare Tunnel ≠ Cloudflare Pages** — Tunnel은 백엔드 공개, 무료 HTTPS 자동
- **Oracle Cloud 계정 생성 시 카드 등록 필요** (무료 티어 확인용, 과금 없음)
- **도메인은 별도 구매** — `.dev` 도메인 (Google Domains) 또는 Cloudflare Registrar (원가)
- **백업 검증**: `ghost_backup.sh` 실행 후 tar 파일 압축 해제 확인
- **기존 Ghost(Pro) 데이터 이관**: 트라이얼 끝나기 전 Admin → Labs → Export 로 JSON 받아 self-hosted에 Import (가이드에 명시)
- Docker 이미지는 공식만 사용 (`docker.io/library/ghost`) — 비공식 이미지 보안 리스크
