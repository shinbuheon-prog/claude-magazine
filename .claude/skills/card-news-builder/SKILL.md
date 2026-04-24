---
name: card-news-builder
description: SNS 카드뉴스 제작 — Hook→핵심→CTA 구조, 7 레이아웃 패턴, Pretendard 폰트. "카드뉴스 제작", "SNS 카드", "1080x1350" 등에 트리거.
allowed-tools: Bash, Read, Write
---

# 카드뉴스 제작 (Card News Builder)

## 언제 사용
- 사용자가 "카드뉴스 제작", "SNS 카드 만들어줘", "1080x1350 카드"를 요청할 때
- 기사 원문을 슬라이드 구조 JSON으로 바꾸고 싶을 때
- `sns-distribution` 단계에서 실제 제작 규칙이 필요할 때

## 절차 (Systematic)

### 1. 기본 원칙 적용
- Hook → 핵심 → CTA 구조를 강제한다.
- 한 장에는 한 메시지만 둔다.
- SNS 카드에는 `Pretendard` 또는 `Noto Sans KR`만 사용한다.
- 상단 15% / 중앙 70% / 하단 15% 안전 구역을 지킨다.

### 2. 레이아웃 패턴 선택
- layout_1: 상단 태그 / 중앙 메인 카피 / 보조 카피 / 하이라이트 / 푸터
- layout_2: 질문형 메인 / 3단 그래픽 / 번호 설명 / 푸터
- layout_3: 단계형 메인 / 아이콘 리스트 / Tip 박스
- layout_4: 좌정렬 메인 / 저장 유도 배지
- layout_5: 핵심 공식 / 프롬프트 카드 2종
- layout_6: 중앙 태그 / 중앙 메인 / 알약 CTA
- layout_7: 카테고리 태그 / 메인 카피 / 그래픽 요소

### 3. 슬라이드 구조 생성
```bash
python pipeline/channel_rewriter.py --draft {draft_path} --channel sns --json
```
- `slides[0]` 는 `hook`
- 마지막 슬라이드는 `cta`
- 중간 슬라이드는 최소 1개 이상 `body`

### 4. 밀도 게이트 검증
```bash
python pipeline/editorial_lint.py --mode card-news --slides-json {slides_json} --source {draft_path}
```
- 리스트형은 항목당 1~2문장
- 서술형은 최소 3문장
- 숫자 언급 시 맥락 문장 포함

## Verify before success
- [ ] Hook / body / CTA 구조가 유지됨
- [ ] 슬라이드 수가 원문 길이에 맞음
- [ ] Pretendard / Noto Sans KR 정책을 지킴
- [ ] `editorial_lint --mode card-news` 통과
