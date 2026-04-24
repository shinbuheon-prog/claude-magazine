---
name: source-validation
description: 기사 소스의 다양성 4규칙 검증 (언어·관점·발행처·시효성). "소스 다양성", "source validation", article_id 언급에 트리거.
allowed-tools: Bash, Read
---

# 소스 다양성 검증 (Source Validation)

## 언제 사용
- 사용자가 "소스 다양성 확인", "source validation" 요청
- article_id가 언급되며 brief 생성 직전
- 편집자가 발행 전 소스 점검 요청

## 절차 (Systematic)

### 1. article_id 확인
- 사용자 요청에서 article_id 추출
- source_registry에 등록된 소스가 3개 이상인지 확인:
```bash
python pipeline/source_registry.py list --article-id {id}
```

### 2. 다양성 검사
```bash
python pipeline/source_diversity.py --article-id {article_id}
```

### 3. 4개 규칙 결과 해석
- **언어 다양성**: 한국어 공식 1+ AND 영문 공식 1+
- **관점 다양성**: pro/neutral/con 중 2개 이상
- **발행처 집중도**: 단일 publisher ≤ 60%
- **시효성**: 30일 이내 1+ AND 365일 초과 1+

### 4. 실패 시 권고
- 언어 실패 → 추가할 언어 소스 예시 안내
- 관점 실패 → 반대 관점 소스 탐색 방향 제시
- 집중도 실패 → 다른 publisher 소스 추가 제안
- 시효성 실패 → 최신 업데이트 확인 권고

### 5. strict 모드 (발행 차단)
편집자가 "엄격 모드"로 요청 시:
```bash
python pipeline/source_diversity.py --article-id {id} --strict
```
- 실패하면 exit 1 — 발행 불가 상태 명시

## Verify before success
- [ ] source_diversity.py 실행 완료
- [ ] 4개 규칙 전부 판정 완료
- [ ] 실패 항목별 구체적 권고 제공
- [ ] strict 모드 요청 시 exit code 정확 반영

## 관련 스킬
- 전체 발행 게이트: publish-gate
- 팩트체크: fact-check-cycle
