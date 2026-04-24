---
name: baoyu-infographic
description: 인사이트 페이지를 비교·타임라인·프로세스 플로우 레이아웃으로 설계하는 래퍼 스킬. "인포그래픽", "insight layout", "비교 도식" 요청에 사용.
allowed-tools: Bash, Read, Write
---

<!-- source: jimliu/baoyu-skills@8c17d77209b030a97d1746928ae348c99fefa775 -->

# Infographic (Magazine Wrapper)

## 언제 사용
- 인사이트 페이지를 숫자 차트 외 다른 시각 레이아웃으로 표현할 때
- `comparison`, `timeline`, `process-flow` 3종 중 하나를 선택할 때
- 월간 매거진의 데이터 설명 페이지를 더 읽기 쉽게 바꾸고 싶을 때

## 절차 (Systematic)

### 1. 레이아웃 선택
- 비교형이면 `comparison`
- 사건/변화 흐름이면 `timeline`
- 단계별 운영 흐름이면 `process-flow`

### 2. 컴포넌트 적용
```bash
cd web
npm run build
```
- `web/src/components/InsightPage.jsx` 의 `layout` prop 으로 렌더링을 전환한다.
- 기본 chart 레이아웃은 유지하고, 나머지 3종은 카드형 시각 구조로 공존한다.

### 3. 데이터 검수
- 레이블, 지표, 단계 설명이 기사 문맥과 맞는지 검토한다.
- 비교표현은 수치 과장 없이 source note 와 함께 쓴다.

## Verify before success
- [ ] `layout="comparison"` 렌더링 확인
- [ ] `layout="timeline"` 렌더링 확인
- [ ] `layout="process-flow"` 렌더링 확인
- [ ] 기존 chart 레이아웃이 깨지지 않음
