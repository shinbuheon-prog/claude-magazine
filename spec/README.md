# Article Standards Spec

`spec/article_standards.yml`은 기사 카테고리별 발행 가능 기준을 정의한다. 목적은 사람이 설명 가능한 pass/fail 기준을 YAML로 고정하고, 모든 품질 파이프라인이 같은 기준을 재사용하게 만드는 것이다.

## 구조
- `common.must_pass`: 모든 카테고리에 공통으로 적용되는 필수 기준
- `categories.<name>.must_pass`: 카테고리별 필수 기준
- `categories.<name>.should_pass`: 있으면 좋은 권장 기준

각 항목은 다음 필드를 가진다.
- `id`: 코드에서 사용하는 안정적인 식별자
- `rule`: 사람이 읽는 설명
- `measure`: 측정식. `eval`이 아니라 제한된 파서로 해석된다.

## measure 패턴
- 단순 존재: `presence`
- 퍼센트: `100% coverage`
- 단순 카운트: `count >= 8`
- 범위: `400 <= words <= 900`
- 복합 조건: `pros >= 2 AND cons >= 2`
- 불리언 플래그: `has_con_section`

## 수정 원칙
- 기존 `id`는 되도록 변경하지 않는다.
- 새 기준을 추가할 때는 먼저 `scripts/validate_standards.py spec/article_standards.yml`로 검증한다.
- 조건식은 제한된 문법만 허용한다. Python 표현식처럼 쓰지 않는다.
- 기준은 가능한 한 짧고 binary하게 유지한다.

## 검증
```bash
python scripts/validate_standards.py spec/article_standards.yml
python pipeline/standards_checker.py --list-categories
python pipeline/standards_checker.py --draft drafts/example.md --category review
```
