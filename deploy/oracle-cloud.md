# Oracle Cloud Always Free 배포 절차

## 개요
Oracle Cloud Always Free는 Ghost self-hosting에 가장 여유로운 무료 티어를 제공한다. Claude Magazine 기준으로 권장 시나리오다.

## 1. 인스턴스 생성
- Compute > Instances > Create instance
- Shape: Ampere A1 Flex
- 권장 스펙: 2~4 OCPU / 12~24GB RAM
- 이미지: Ubuntu 22.04 ARM64
- SSH 키 등록

## 2. 서버 초기 설정
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker version
docker compose version
```

## 3. 저장소 배포
```bash
git clone <your-repo-url> claude-magazine
cd claude-magazine/deploy
cp .env.deploy.example .env.deploy
vi .env.deploy
docker compose --env-file .env.deploy up -d
docker compose ps
```

## 4. HTTPS 연결
- 서버의 2368 포트는 외부에 직접 열지 않는 편이 안전하다.
- Cloudflare Tunnel로 `magazine.your-domain.dev`를 연결한다.
- 상세는 [cloudflare-tunnel.md](C:/Users/shin.buheon/claude-magazine/deploy/cloudflare-tunnel.md) 참고.

## 5. Ghost 초기화
- 브라우저에서 `https://magazine.your-domain.dev/ghost/`
- 관리자 계정 생성
- Integrations > Custom Integration 생성
- Admin API Key 발급

## 6. 로컬 파이프라인 연결
루트 `.env`에 다음을 반영한다.

```env
GHOST_ADMIN_API_URL=https://magazine.your-domain.dev
GHOST_ADMIN_API_KEY=kid:secret
```

검증:

```bash
python scripts/check_env.py --only ghost
python pipeline/ghost_client.py --dry-run
```
