# TASK_017 — PII 비식별화 파이프라인 (pii_masker.py)

## 메타
- **status**: todo
- **prerequisites**: 없음
- **예상 소요**: 45분
- **서브에이전트 분할**: 불필요
- **Phase**: 3 (법적 리스크 차단)

---

## 목적
인터뷰·내부 문서·제보 자료를 Claude API에 보내기 전 **자동 비식별화**.
리포트 인용: _"2026-01-22 AI 기본법 시행 + 개인정보보호위원회 생성형 AI 개발·활용 안내서 준수."_

---

## 구현 명세

### 생성할 파일: `pipeline/pii_masker.py`

### CLI
```bash
# 파일 비식별화
python pipeline/pii_masker.py --input interview.md --output interview_masked.md

# 인라인 (stdin → stdout)
cat interview.md | python pipeline/pii_masker.py > masked.md

# 역매핑 테이블 별도 저장
python pipeline/pii_masker.py --input interview.md --mapping-out mapping.json

# 사후 복원
python pipeline/pii_masker.py --restore draft.md --mapping mapping.json --output restored.md

# 탐지만 (마스킹 없이 리스트)
python pipeline/pii_masker.py --input interview.md --detect-only
```

### 탐지 패턴 (우선순위 순)

| # | 분류 | 패턴 | 마스킹 예시 |
|---|---|---|---|
| 1 | 주민번호 | `\d{6}-[1-4]\d{6}` | `[KRN_001]` |
| 2 | 전화번호 | `01[0-9]-\d{3,4}-\d{4}` | `[PHONE_001]` |
| 3 | 이메일 | RFC 5322 | `[EMAIL_001]` |
| 4 | 신용카드 | `\d{4}-\d{4}-\d{4}-\d{4}` | `[CARD_001]` |
| 5 | 계좌번호 | `\d{3,6}-\d{2,6}-\d{4,10}` | `[ACCT_001]` |
| 6 | 사업자번호 | `\d{3}-\d{2}-\d{5}` | `[BIZ_001]` |
| 7 | 한국 이름 | Claude Haiku로 NER 호출 (오탐 보정) | `[PERSON_001]` |
| 8 | 회사 내부 시스템명 | `.env`에 `PII_INTERNAL_TERMS` 패턴 로드 | `[SYSTEM_001]` |
| 9 | 주소 | 시·도·구·동 매칭 + 번지 | `[ADDR_001]` |
| 10 | IP 주소 | IPv4/IPv6 | `[IP_001]` |

### 핵심 설계
- **결정적 마스킹**: 같은 이름은 항상 같은 토큰 (`[PERSON_001]`)
- **역매핑 테이블**: `{token: original}` JSON으로 별도 저장 (인간만 접근)
- **Claude 호출 직전 마스킹, 응답 수신 후 복원** — 원문이 Claude 서버에 저장되지 않도록

### 함수 시그니처
```python
def mask_text(text: str, internal_terms: list[str] | None = None) -> tuple[str, dict]:
    """
    반환: (masked_text, mapping_dict)
    mapping_dict: {"[PERSON_001]": "홍길동", "[EMAIL_001]": "a@b.com", ...}
    """

def restore_text(masked_text: str, mapping: dict) -> str:
    """마스킹 토큰을 원문으로 복원"""

def detect_pii(text: str) -> list[dict]:
    """
    마스킹 없이 탐지만.
    반환: [{"type": "phone", "value": "010-1234-5678", "position": [42, 58]}, ...]
    """
```

### pipeline 통합 헬퍼 (자동 파이프라인)
```python
def with_pii_protection(claude_call_fn, text: str, **kwargs):
    """
    사용 패턴:
      result = with_pii_protection(
          lambda t: run_factcheck(t, sources),
          text=raw_interview,
      )
    내부: mask → Claude 호출 → restore
    """
```

### 출력 형식
```
=== PII 비식별화 ===
입력: interview.md (1,234 bytes)

탐지:
  - PERSON: 3건
  - EMAIL: 2건
  - PHONE: 1건
  - COMPANY_INTERNAL: 2건

출력: interview_masked.md (1,198 bytes)
매핑: interview_mapping.json (8 entries)

⚠️  매핑 파일은 민감 — data/ 외부로 유출 금지
```

---

## 완료 조건
- [ ] `pipeline/pii_masker.py` 생성
- [ ] 10개 패턴 전부 탐지
- [ ] `mask_text`, `restore_text`, `detect_pii`, `with_pii_protection` 구현
- [ ] 결정적 마스킹 확인 (같은 이름 → 같은 토큰)
- [ ] 역매핑 JSON은 기본 `data/pii_mappings/` 저장 (.gitignore 추가)
- [ ] 스모크 테스트: 가짜 인터뷰 텍스트에서 마스킹 → 복원 round-trip
- [ ] `.gitignore`에 `data/pii_mappings/` 추가

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_017 implemented
```

---

## 주의사항
- **매핑 JSON은 절대 커밋 금지** — .gitignore 필수
- 한국 이름 NER은 Haiku 4.5로 배치 호출 (단순 패턴은 놓치기 쉬움)
- 마스킹 토큰은 Claude가 의미 유추 못하도록 번호만 사용 (`[PERSON_001]`, `[PERSON_002]`)
