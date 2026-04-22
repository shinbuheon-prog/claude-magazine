# Fly.io 배포 절차

## 개요
Fly.io는 빠른 PoC와 작은 트래픽에 적합한 대안이다. 다만 스토리지와 리전 선택은 Oracle Cloud보다 제한적이다.

## 준비
- Fly.io 계정
- `flyctl` 설치
- SMTP 계정

## 예시 흐름
```bash
fly auth login
cd deploy
fly launch --name claude-magazine-ghost --no-deploy
```

이후:
- 내부 포트를 2368로 맞춘다.
- persistent volume을 생성한다.
- `.env.deploy` 값을 Fly secrets 또는 env로 옮긴다.
- `docker-compose.yml`의 환경변수를 Fly 설정으로 매핑한다.

## 권장 사항
- production URL을 먼저 정하고 `GHOST_URL`과 일치시킨다.
- volume 없이는 SQLite 데이터가 유실되므로 반드시 persistent volume을 사용한다.
- 메일 발송은 SMTP provider를 별도 연결한다.

## 검증
배포 후 다음만 확인하면 충분하다.
- `/ghost/` 접속 가능
- Admin API Key 발급 가능
- `python scripts/check_env.py --only ghost` 통과
