# TASK_043 — 이미지 생성 provider 매트릭스 + illustration_hook 백엔드 어댑터 설계

## 메타
- **status**: todo
- **prerequisites**: TASK_040 (illustration_hook.py placeholder)
- **예상 소요**: 90~120분
- **태스크 유형**: **조사·설계 + 어댑터 스켈레톤 (실제 API 호출 구현 아님)**
- **서브에이전트 분할**: 불필요
- **Phase**: 5 확장 후속 (이미지 백엔드 옵션 선정)

---

## 목적
TASK_040에서 `pipeline/illustration_hook.py`가 placeholder PNG만 생성 중. 실제 이미지 생성 백엔드를 붙이기 전에 **provider 비교 + 무료 발행 원칙 정합성 검증 + 어댑터 인터페이스 설계**.
본 태스크는 **provider 비교 문서 + 어댑터 스켈레톤 코드**까지. 실제 API 연동·이미지 생성 호출은 후속 태스크(TASK_045 후보)로 분리.

**중요 전제**: Claude 자체는 이미지 생성을 수행하지 않음 (이해만 가능). 외부 provider 선택이 필수.

---

## 조사 범위

### 1. Provider 후보 매트릭스 (최소 5개)
다음 관점으로 provider 비교:
| Provider | 가격 | 무료 tier | 품질(매거진톤) | 한국어 프롬프트 | 라이선스 | API 안정성 |
|---|---|---|---|---|---|---|
| OpenAI DALL·E 3 | | | | | | |
| Google Imagen / Gemini | | | | | | |
| Stable Diffusion (로컬) | | | | | | |
| Replicate | | | | | | |
| Stability AI API | | | | | | |
| (기타 후보) | | | | | | |

**필수 평가 축**:
- **무료 tier 한도**: 월간 매거진 80페이지 + 주간 브리프 발행 규모 감당 가능한지
- **한국어 프롬프트**: 한글 텍스트 생성 품질 (카드뉴스 레이아웃에 들어가는 한글)
- **상업적 사용 라이선스**: 매거진 무료 발행이지만 출판물 = 상업적 사용 판정 가능
- **로컬 실행 가능성**: Stable Diffusion 로컬 구동으로 비용 0 가능한지

### 2. 무료 발행 원칙 정합성
참조: [project_claude_magazine.md](../../../.claude/projects/C--Users-shin-buheon/memory/project_claude_magazine.md) "전면 무료 발행"
- 월 운영비 상한 제안 (편집자 개인 부담 가능 수준)
- 무료 tier 초과 시 자동 degrade 정책 (placeholder fallback 등)
- 비용 모니터링 방식 (`logs/illustrations.jsonl` 확장)

### 3. 어댑터 인터페이스 설계
`pipeline/illustration_hook.py`가 호출할 공통 인터페이스:
```python
# 제안 시그니처 (확정은 설계 문서에서)
class IllustrationProvider(ABC):
    name: str
    requires_env: list[str]

    @abstractmethod
    def generate(
        self,
        prompt: str,
        size: tuple[int, int],
        article_id: str,
    ) -> IllustrationResult: ...

@dataclass
class IllustrationResult:
    image_path: Path
    provider: str
    model: str
    request_id: str
    cost_estimate: float | None
    license: str
```

### 4. 현재 illustration_hook 연결 방식
- `_create_placeholder()` 자리에 어댑터 호출을 어떻게 주입할지
- provider 선택 우선순위 (환경변수 기반 fallback chain)
- 실패 시 placeholder 유지 (회귀 없음 보장)

---

## 산출물

### 1. `docs/illustration_backend_options.md` (신규, 필수)
섹션 구성:
1. **Provider 매트릭스** (최소 5개 비교)
2. **무료 발행 원칙 정합성 분석** — 각 provider별 월 예상 비용
3. **권장 1차안** (무료 tier 또는 로컬 기준)
4. **권장 2차안** (품질 우선, 유료 허용 시)
5. **라이선스 표 정리** (상업적 사용·저작권 귀속)
6. **어댑터 인터페이스 스펙** (ABC 정의 + 데이터클래스 + 환경변수 명명 규칙)
7. **fallback 체인 정책** (실패 시 placeholder 복귀)
8. **비용 모니터링 설계** (`logs/illustrations.jsonl` 필드 확장안)
9. **후속 실구현 태스크 범위** (TASK_045 스케치)

### 2. `pipeline/illustration_providers/__init__.py` (신규, 스켈레톤)
- `IllustrationProvider` ABC 정의만
- `IllustrationResult` 데이터클래스 정의만
- **실제 provider 구현체는 본 태스크 범위 외** (raise NotImplementedError 스텁)

### 3. `pipeline/illustration_providers/placeholder.py` (신규, 기본 구현만)
- 기존 `_create_placeholder()` 로직을 ABC 계약에 맞춰 래핑
- fallback 체인의 마지막 단계로 항상 동작하도록 보장
- 본 태스크 완료 시 `illustration_hook.py`가 이 래퍼를 사용하도록 최소 수정 허용

### 4. `tasks/TASK_045_draft.md` (선택)
설계안 기반 실구현 태스크 초안 (status: draft) — 어떤 provider를 1차로 붙일지 사용자 결정 후 확정.

---

## 조사 제약 조건
- **무료 발행 원칙 우선**: 1차 권장안은 월 $0 또는 편집자 개인 부담 최소(~$10 이하) 옵션
- **라이선스 함정 주의**: 학습 데이터 상업적 사용 금지 provider는 권장안에서 제외
- **한국어 품질 필수**: 한글 프롬프트 대응 못하는 provider는 리스크 섹션에 명시
- **장기 안정성**: 베타·리버스엔지니어링 API 제외 ([baoyu-skills audit](../docs/baoyu_skills_audit.md) 동일 원칙)

---

## 탈락시킬 옵션 (명시적 제외)
- 리버스엔지니어링 기반 비공식 API (예: Gemini Web 비공식 래퍼) — TASK_025 Pass/Fail 충돌
- 학습 데이터 상업적 사용 명시 금지인 provider
- 생성 이미지 소유권이 provider에게 귀속되는 provider (매거진 재사용 불가)

---

## 완료 조건 (Definition of Done)
- [ ] `docs/illustration_backend_options.md` 9 섹션 모두 채워짐
- [ ] 최소 5개 provider 비교 (가격·라이선스·한국어·라이선스 명시)
- [ ] 1차 권장안 + 2차 권장안 각각 선정 근거 2문장 이상
- [ ] 어댑터 인터페이스 ABC 스펙 문서화 (시그니처·예외 체계)
- [ ] fallback 체인 정책 명시 (실패 시 placeholder 유지)
- [ ] `pipeline/illustration_providers/__init__.py` ABC + 데이터클래스 정의
- [ ] `pipeline/illustration_providers/placeholder.py` 기존 로직 래핑, 기존 테스트 회귀 없음
- [ ] `illustration_hook.py`가 placeholder provider를 경유해도 기존 동작 동일
- [ ] `logs/illustrations.jsonl` 필드 확장안 제안 (cost_estimate·provider_name 추가 여부)
- [ ] 탈락 옵션 섹션 명시

---

## 후속 태스크 (본 태스크 범위 외)
- **TASK_045 후보**: 1차 권장안 provider 실구현 (예: local Stable Diffusion 또는 무료 tier API)
- **TASK_046 후보**: 비용 모니터링 대시보드 위젯 (TASK_028 운영 투명성 대시보드 연장)

---

## 완료 처리
```bash
python codex_workflow.py update TASK_043 implemented   # 문서 + 스켈레톤 완료 후
python codex_workflow.py update TASK_043 merged        # 검토 완료 후
```
