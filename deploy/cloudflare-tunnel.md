# Cloudflare Tunnel 가이드

Cloudflare Tunnel을 쓰면 공개 IP를 직접 열지 않고도 무료 HTTPS와 커스텀 도메인을 연결할 수 있다.

## 준비
- Cloudflare 계정
- Cloudflare에 연결된 도메인
- `cloudflared` 설치

## 기본 절차
```bash
cloudflared tunnel login
cloudflared tunnel create claude-magazine
cloudflared tunnel route dns claude-magazine magazine.your-domain.dev
cloudflared tunnel run --url http://localhost:2368 claude-magazine
```

## systemd 권장
운영 서버에서는 foreground 실행보다 systemd 서비스 등록이 안전하다.

## 확인 포인트
- `https://magazine.your-domain.dev` 접속
- `https://magazine.your-domain.dev/ghost/` 접속
- 루트 `.env`의 `GHOST_ADMIN_API_URL`과 정확히 동일해야 한다.

## 보안 메모
- 2368 포트를 공인 인터넷에 직접 노출하지 않아도 된다.
- 관리자 페이지 접근 보호는 Cloudflare Access와 함께 고려할 수 있다.
