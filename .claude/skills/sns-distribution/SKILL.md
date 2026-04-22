---
name: sns-distribution
description: 발행된 기사를 4개 채널(sns·instagram·linkedin·twitter)로 재가공 + 이미지 자산 체크. "SNS 재가공", "sns distribution", "카드뉴스"에 트리거.
allowed-tools: Bash, Read
---

# SNS 배포 (SNS Distribution)

## 언제 사용
- 사용자가 "SNS 재가공해줘", "카드뉴스 만들어줘" 요청
- Ghost published 이벤트 후 자동 트리거 (n8n workflow_3와 연동)
- 편집자가 특정 기사의 SNS 자산 상태 확인 요청

## 절차 (Systematic)

### 1. 대상 기사 확인
- 사용자 요청에서 다음 정보 추출:
  - draft_path 또는 ghost post id
  - post_slug (자산 파일명 매칭용)
  - 월 (YYYY-MM, 없으면 현재월)

### 2. 자산 먼저 체크 (API 호출 전)
```bash
python pipeline/channel_rewriter.py --draft {draft_path} --channel sns \
    --post-slug {slug} --month {YYYY-MM} --assets-report
```
- missing_assets 리스트 확인
- 누락된 이미지 있으면 Claude Design 링크 안내

### 3. 채널별 텍스트 재가공
다음 순서로 4개 채널 실행:
```bash
# sns 카드뉴스 (1080x1080 × 3장)
python pipeline/channel_rewriter.py --draft {path} --channel sns --post-slug {slug}

# instagram 피드 + 스토리
python pipeline/channel_rewriter.py --draft {path} --channel instagram --post-slug {slug}

# linkedin 헤더
python pipeline/channel_rewriter.py --draft {path} --channel linkedin --post-slug {slug}

# twitter 카드
python pipeline/channel_rewriter.py --draft {path} --channel twitter --post-slug {slug}
```

### 4. 통합 리포트
각 채널별로:
- 재가공 텍스트 (Haiku 출력)
- 자산 체크 결과 (존재/누락)
- 라이선스 등록 필요 여부

### 5. 라이선스 체크
```bash
python scripts/check_sns_assets.py --month {YYYY-MM} --post-slug {slug}
```
- licenses.json에 등록되지 않은 고아 파일 경고

## Verify before success
- [ ] 4개 채널 전부 재가공 성공
- [ ] 각 채널별 자산 상태 보고됨
- [ ] 누락 자산에 대해 Claude Design 안내 제공
- [ ] 라이선스 미등록 자산 경고 출력
- [ ] 텍스트·자산 경로가 즉시 SNS 게시 가능한 형태로 정리됨

## 비용 참고
- Haiku 4.5 호출 × 4 = 약 $0.02 per article
- 이미지는 생성 안 함 (Claude Design 수동)

## 관련 스킬
- 발행 전 검증: publish-gate
- 원본 기사 검토: editorial-review
