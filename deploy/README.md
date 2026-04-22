# Ghost Self-Hosted 배포 가이드

Claude Magazine은 Ghost(Pro) 대신 Ghost 오픈소스를 셀프호스팅해도 기존 `pipeline/ghost_client.py`를 그대로 재사용할 수 있다. 바뀌는 것은 `GHOST_ADMIN_API_URL`과 `GHOST_ADMIN_API_KEY`뿐이다.

## 왜 Self-Hosted인가
- 비용: Ghost(Pro) 월 $18+ 대신 인프라 무료 티어 + 무료 SMTP 조합으로 월 고정비를 거의 0에 가깝게 유지할 수 있다.
- 코드 재사용: Ghost Admin API, JWT 인증, newsletter 발송 플로우가 동일하다.
- 운영 범위: MVP 규모(주 1회 발행, 구독자 1,000명 미만)에서는 SQLite 단일 컨테이너로 충분하다.

## 빠른 시작
1. `deploy/.env.deploy.example`를 복사해 `.env.deploy`를 만든다.
2. `GHOST_URL`, `MAIL_FROM`, SMTP 값을 채운다.
3. `cd deploy`
4. `docker compose --env-file .env.deploy up -d`
5. 브라우저에서 `http://localhost:2368/ghost/` 또는 터널/도메인 URL로 접속해 Ghost Admin 초기 계정을 만든다.
6. Ghost Admin > Settings > Integrations 에서 Admin API Key를 발급한다.
7. 루트 `.env`의 `GHOST_ADMIN_API_URL`, `GHOST_ADMIN_API_KEY`를 self-hosted 값으로 교체한다.
8. `python scripts/check_env.py --only ghost`로 연결을 검증한다.

## 시나리오 1: Oracle Cloud Always Free
- 권장 이유: ARM 4 OCPU / 24GB RAM / 200GB 블록 스토리지 무료 티어가 장기 운영에 가장 유리하다.
- OS: Ubuntu 22.04 ARM64
- 절차:
  - 인스턴스를 생성하고 2368 포트를 내부에서만 사용한다.
  - Docker Engine과 Docker Compose plugin을 설치한다.
  - 저장소를 clone 후 `deploy/.env.deploy`를 작성한다.
  - `docker compose --env-file .env.deploy up -d`
  - HTTPS는 Cloudflare Tunnel로 붙인다.
- 상세 절차는 [oracle-cloud.md](C:/Users/shin.buheon/claude-magazine/deploy/oracle-cloud.md) 참고.

## 시나리오 2: Fly.io
- 장점: 작은 단일 앱 배포가 간단하고 `*.fly.dev` 도메인을 바로 쓸 수 있다.
- 적합성: 무료/저비용 대안으로 충분하지만, 스토리지 정책과 지역 선택은 Oracle보다 제약이 있다.
- 상세 절차는 [fly-io.md](C:/Users/shin.buheon/claude-magazine/deploy/fly-io.md) 참고.

## 시나리오 3: 로컬 테스트
- 목적: 실제 Ghost 연결, Admin API 키 발급, 기존 파이프라인 호환성 검증
- 명령:

```bash
cd deploy
cp .env.deploy.example .env.deploy
docker compose --env-file .env.deploy up -d
```

- 확인:
  - `http://localhost:2368`
  - `http://localhost:2368/ghost/`
  - `docker compose ps`

## 운영 체크리스트
- 백업: `deploy/scripts/ghost_backup.sh`를 매일 1회 cron으로 실행
- 업데이트: `deploy/scripts/ghost_update.sh`를 월 1회 실행
- 두 스크립트는 기본적으로 `deploy/.env.deploy`를 사용하며, 다른 파일을 쓰려면 `ENV_FILE=/path/to/file`로 override한다.
- HTTPS: Cloudflare Tunnel 사용 권장
- SMTP: Resend, Mailgun, SES 중 하나 사용
- 데이터 이관: Ghost(Pro) 종료 전에 Admin > Labs > Export로 JSON export 후 self-hosted에 import

## MySQL 마이그레이션 기준
- 기준: 구독자 10,000명 초과 또는 동시 쓰기/대량 메일 발송으로 SQLite 락 경합이 발생할 때
- 방향:
  - MySQL 8.x 별도 컨테이너 추가
  - `database__client=mysql`
  - `database__connection__host`, `user`, `password`, `database` 환경변수 추가
  - Ghost export/import 또는 공식 DB migration 절차 적용

MVP 단계에서는 SQLite가 운영 복잡도를 가장 낮춘다.
