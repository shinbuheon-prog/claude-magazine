# SMTP 연동 가이드

Ghost newsletter 발송은 SMTP가 필요하다. Claude Magazine 기준으로는 Resend가 가장 단순하다.

## 1. Resend 권장 설정
- 장점: 설정이 간단하고 개발 단계 무료 한도가 충분하다.
- 예시:

```env
SMTP_SERVICE=Resend
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=resend
SMTP_PASS=re_xxxxxxxxxxxx
MAIL_FROM=noreply@your-domain.dev
```

## 2. Mailgun 대안
```env
SMTP_SERVICE=Mailgun
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=postmaster@mg.your-domain.dev
SMTP_PASS=...
```

## 3. Amazon SES 대안
```env
SMTP_SERVICE=SES
SMTP_HOST=email-smtp.ap-northeast-2.amazonaws.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=...
SMTP_PASS=...
```

## DNS 권장
- SPF
- DKIM
- DMARC

설정하지 않으면 수신률이 떨어진다.

## 발송 검증
- Ghost Admin에서 test newsletter를 발송한다.
- 루트 파이프라인에서는 `python pipeline/ghost_client.py --send-newsletter`로 실제 연결 확인 가능하다.

## 쿼터 메모
- 무료 티어는 월간 또는 일간 발송 제한이 있으므로 구독자 수와 주간 발송 횟수를 같이 계산해야 한다.
